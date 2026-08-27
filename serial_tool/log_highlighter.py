# -*- coding: utf-8 -*-
"""日志关键词高亮：基于 QSyntaxHighlighter，仅在日志上按关键词着色。"""

import re

from PyQt5.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor


class KeywordHighlighter(QSyntaxHighlighter):
    """按关键词列表对文本块高亮（不区分大小写）。"""

    def __init__(self, document, rules=()):
        super().__init__(document)
        self._rules = []
        self.set_rules(rules)

    def set_rules(self, rules):
        """设置高亮规则；rules: [(关键词, 颜色十六进制), ...]。"""
        compiled = []
        for keyword, color in rules:
            kw = keyword.strip()
            if not kw:
                continue
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(color))
            compiled.append((re.compile(re.escape(kw), re.IGNORECASE), fmt))
        self._rules = compiled
        self.rehighlight()

    def highlightBlock(self, text):
        for pattern, fmt in self._rules:
            for m in pattern.finditer(text):
                self.setFormat(m.start(), m.end() - m.start(), fmt)
