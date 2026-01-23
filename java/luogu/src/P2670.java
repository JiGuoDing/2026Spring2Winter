import java.util.Scanner;

public class P2670 {
    public static void main(String[] args) {
        // 创建读取器
        Scanner scanner = new Scanner(System.in);

        // 读取行数 n 和 列数 m
        int n = scanner.nextInt();
        int m = scanner.nextInt();
        // 吸收换行符，避免影响后续读取
        scanner.nextLine();

        // 存储雷区布局
        char[][] mineField = new char[n][m];
        for (int i = 0; i < n; i++) {
            String line = scanner.nextLine();
            mineField[i] = line.toCharArray();
        }

        // 定义 8 个方向的偏移量
        int [][] directions = {
            {-1, -1}, {-1, 0}, {-1, 1},
            {0, -1},          {0, 1},
            {1, -1}, {1, 0}, {1, 1}
        };

        // 遍历每个格子并输出结果
        for (int i = 0; i < n; i++) {
            // 拼接每行结果，效率更高
            StringBuilder sb = new StringBuilder();
            for (int j = 0; j < m; j++) {
                if (mineField[i][j] == '*') {
                    // 该格为地雷，直接添加 '*'
                    sb.append('*');
                } else {
                    int count = 0;
                    for (int[] direction : directions) {
                        int newRow = i + direction[0];
                        int newCol = j + direction[1];
                        // 检查新位置是否在边界内且为地雷
                        if (newRow >= 0 && newRow < n && newCol >= 0 && newCol < m) {
                            if (mineField[newRow][newCol] == '*') {
                                count++;
                            }
                        }
                    }
                    // 添加地雷计数
                    sb.append(count);
                }
            }
            System.out.println(sb.toString());
        }
        scanner.close();
    }
}
