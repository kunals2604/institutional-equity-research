#!/usr/bin/env python3
"""Usage: filings_pageof.py TXT LINE [LINE...] -> PDF page number (1-based) of each line in a pdftotext output (form-feed separated)."""
import sys
path = sys.argv[1]
lines = open(path, encoding="utf-8", errors="replace").read().split("\n")
for ln in map(int, sys.argv[2:]):
    page = 1 + sum(l.count("\f") for l in lines[:ln-1])
    print(ln, "-> PDF p.", page)
