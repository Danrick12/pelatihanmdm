#!/usr/bin/env python3
"""Build MDM_Kelompok5_DJBC.ipynb - Complete MDM pipeline notebook for Google Colab"""
import json, os

OUTPUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      'notebooks', 'MDM_Kelompok5_DJBC.ipynb')
os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)

def md(src):
    return {"cell_type":"markdown","metadata":{},"source":[src]}
def cd(src):
    return {"cell_type":"code","execution_count":None,"metadata":{},"outputs":[],"source":[src]}

C = []
