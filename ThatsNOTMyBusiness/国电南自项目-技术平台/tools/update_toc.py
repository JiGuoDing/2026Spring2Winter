# -*- coding: utf-8 -*-
"""用 Word COM 打开重建后的 docx，更新目录域与页码，保存关闭。"""
import win32com.client as win32

PATH = r"Q:\workspace\2026Spring2Winter\ThatsNOTMyBusiness\国电南自项目-技术平台\交付物\集团级多租户技术平台架构设计方案（初版）-v0.1-润色版.docx"

app = win32.DispatchEx("Word.Application")
app.Visible = False
app.DisplayAlerts = 0
try:
    doc = app.Documents.Open(PATH, False, False)
    print("opened:", doc.Name, "readonly:", doc.ReadOnly)
    print("pages before:", doc.ComputeStatistics(2))
    print("toc count:", doc.TablesOfContents.Count)

    doc.ActiveWindow.View.Type = 3  # wdPrintView
    # 1) 先整体更新域（TOC 域会被刷新）
    doc.Fields.Update()
    print("fields updated")
    # 2) 再逐条更新 TOC（失败不致命，记录报错）
    for i in range(1, doc.TablesOfContents.Count + 1):
        try:
            doc.TablesOfContents(i).Update()
            print("toc updated:", i)
        except Exception as e:
            print("toc update failed:", i, e)
    doc.Repaginate()
    print("pages after:", doc.ComputeStatistics(2))
    doc.Save()
    doc.Close(0)
    print("saved and closed")
finally:
    app.Quit()
