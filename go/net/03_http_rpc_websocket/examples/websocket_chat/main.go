package main

import (
	"bufio"
	"bytes"
	"crypto/rand"
	"crypto/sha1"
	"encoding/base64"
	"encoding/binary"
	"fmt"
	"io"
	"log"
	"net"
	"net/http"
	"net/http/httptest"
	"net/url"
	"strings"
	"sync"
	"time"
)

const wsMagicGUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

type wsPeer struct {
	name string
	conn net.Conn
	mu   sync.Mutex
}

func (p *wsPeer) writeText(message string, masked bool) error {
	return writeWebSocketFrame(p.conn, 0x1, []byte(message), masked)
}

func (p *wsPeer) Close() error {
	return p.conn.Close()
}

func (p *wsPeer) readText() (string, error) {
	_ = p.conn.SetReadDeadline(time.Now().Add(2 * time.Second))
	opcode, payload, err := readWebSocketFrame(p.conn)
	if err != nil {
		return "", err
	}
	if opcode == 0x8 {
		return "", io.EOF
	}
	return string(payload), nil
}

type hub struct {
	mu      sync.Mutex
	clients map[*wsPeer]struct{}
}

func newHub() *hub {
	return &hub{clients: make(map[*wsPeer]struct{})}
}

func (h *hub) add(client *wsPeer) {
	h.mu.Lock()
	defer h.mu.Unlock()
	h.clients[client] = struct{}{}
}

func (h *hub) remove(client *wsPeer) {
	h.mu.Lock()
	defer h.mu.Unlock()
	delete(h.clients, client)
}

func (h *hub) broadcast(message string) {
	h.mu.Lock()
	clients := make([]*wsPeer, 0, len(h.clients))
	for client := range h.clients {
		clients = append(clients, client)
	}
	h.mu.Unlock()

	for _, client := range clients {
		client.mu.Lock()
		err := client.writeText(message, false)
		client.mu.Unlock()
		if err != nil {
			log.Println("broadcast error:", err)
		}
	}
}

func main() {
	h := newHub()

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/ws" {
			http.NotFound(w, r)
			return
		}
		conn, err := upgradeWebSocket(w, r)
		if err != nil {
			log.Println("upgrade error:", err)
			return
		}
		name := r.URL.Query().Get("name")
		if name == "" {
			name = "guest"
		}
		peer := &wsPeer{name: name, conn: conn}
		h.add(peer)
		defer func() {
			h.remove(peer)
			_ = conn.Close()
		}()

		for {
			opcode, payload, err := readWebSocketFrame(conn)
			if err != nil {
				return
			}
			if opcode == 0x8 {
				return
			}
			message := fmt.Sprintf("%s: %s", name, string(payload))
			h.broadcast(message)
		}
	}))
	defer server.Close()

	wsBaseURL := "ws" + strings.TrimPrefix(server.URL, "http") + "/ws"
	aliceConn := mustDialWebSocket(wsBaseURL, "alice")
	defer aliceConn.Close()
	bobConn := mustDialWebSocket(wsBaseURL, "bob")
	defer bobConn.Close()

	if err := aliceConn.writeText("hello from alice", true); err != nil {
		log.Fatal(err)
	}
	if err := bobConn.writeText("hello from bob", true); err != nil {
		log.Fatal(err)
	}

	fmt.Println("alice received:")
	for i := 0; i < 2; i++ {
		message, err := aliceConn.readText()
		if err != nil {
			log.Fatal(err)
		}
		fmt.Println(" ", message)
	}

	fmt.Println("bob received:")
	for i := 0; i < 2; i++ {
		message, err := bobConn.readText()
		if err != nil {
			log.Fatal(err)
		}
		fmt.Println(" ", message)
	}
}

func mustDialWebSocket(baseURL, name string) *wsPeer {
	parsedURL, err := url.Parse(baseURL)
	if err != nil {
		log.Fatal(err)
	}
	parsedURL.RawQuery = "name=" + url.QueryEscape(name)

	conn, err := net.Dial("tcp", parsedURL.Host)
	if err != nil {
		log.Fatal(err)
	}

	keyBytes := make([]byte, 16)
	if _, err := rand.Read(keyBytes); err != nil {
		log.Fatal(err)
	}
	key := base64.StdEncoding.EncodeToString(keyBytes)
	request := fmt.Sprintf(
		"GET %s HTTP/1.1\r\nHost: %s\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: %s\r\nSec-WebSocket-Version: 13\r\n\r\n",
		parsedURL.RequestURI(), parsedURL.Host, key,
	)
	if _, err := io.WriteString(conn, request); err != nil {
		log.Fatal(err)
	}

	reader := bufio.NewReader(conn)
	statusLine, err := reader.ReadString('\n')
	if err != nil {
		log.Fatal(err)
	}
	if !strings.Contains(statusLine, "101") {
		log.Fatal("websocket handshake failed: ", strings.TrimSpace(statusLine))
	}
	for {
		line, err := reader.ReadString('\n')
		if err != nil {
			log.Fatal(err)
		}
		if line == "\r\n" {
			break
		}
	}

	return &wsPeer{name: name, conn: conn}
}

func upgradeWebSocket(w http.ResponseWriter, r *http.Request) (net.Conn, error) {
	hijacker, ok := w.(http.Hijacker)
	if !ok {
		return nil, fmt.Errorf("http server does not support hijacking")
	}
	conn, buf, err := hijacker.Hijack()
	if err != nil {
		return nil, err
	}

	key := r.Header.Get("Sec-WebSocket-Key")
	accept := websocketAcceptKey(key)
	response := fmt.Sprintf(
		"HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: %s\r\n\r\n",
		accept,
	)
	if _, err := buf.WriteString(response); err != nil {
		_ = conn.Close()
		return nil, err
	}
	if err := buf.Flush(); err != nil {
		_ = conn.Close()
		return nil, err
	}
	return conn, nil
}

func websocketAcceptKey(key string) string {
	h := sha1.New()
	_, _ = h.Write([]byte(key + wsMagicGUID))
	return base64.StdEncoding.EncodeToString(h.Sum(nil))
}

func writeWebSocketFrame(conn net.Conn, opcode byte, payload []byte, masked bool) error {
	var header bytes.Buffer
	header.WriteByte(0x80 | opcode)

	length := len(payload)
	maskBit := byte(0)
	if masked {
		maskBit = 0x80
	}

	switch {
	case length < 126:
		header.WriteByte(maskBit | byte(length))
	case length <= 65535:
		header.WriteByte(maskBit | 126)
		var extended [2]byte
		binary.BigEndian.PutUint16(extended[:], uint16(length))
		header.Write(extended[:])
	default:
		header.WriteByte(maskBit | 127)
		var extended [8]byte
		binary.BigEndian.PutUint64(extended[:], uint64(length))
		header.Write(extended[:])
	}

	if !masked {
		_, err := conn.Write(append(header.Bytes(), payload...))
		return err
	}

	var maskKey [4]byte
	if _, err := rand.Read(maskKey[:]); err != nil {
		return err
	}
	header.Write(maskKey[:])
	maskedPayload := make([]byte, len(payload))
	for index, b := range payload {
		maskedPayload[index] = b ^ maskKey[index%4]
	}
	_, err := conn.Write(append(header.Bytes(), maskedPayload...))
	return err
}

func readWebSocketFrame(conn net.Conn) (byte, []byte, error) {
	var header [2]byte
	if _, err := io.ReadFull(conn, header[:]); err != nil {
		return 0, nil, err
	}

	opcode := header[0] & 0x0F
	masked := header[1]&0x80 != 0
	length := int(header[1] & 0x7F)

	switch length {
	case 126:
		var extended [2]byte
		if _, err := io.ReadFull(conn, extended[:]); err != nil {
			return 0, nil, err
		}
		length = int(binary.BigEndian.Uint16(extended[:]))
	case 127:
		var extended [8]byte
		if _, err := io.ReadFull(conn, extended[:]); err != nil {
			return 0, nil, err
		}
		length = int(binary.BigEndian.Uint64(extended[:]))
	}

	var maskKey [4]byte
	if masked {
		if _, err := io.ReadFull(conn, maskKey[:]); err != nil {
			return 0, nil, err
		}
	}

	payload := make([]byte, length)
	if _, err := io.ReadFull(conn, payload); err != nil {
		return 0, nil, err
	}
	if masked {
		for index := range payload {
			payload[index] ^= maskKey[index%4]
		}
	}
	return opcode, payload, nil
}
