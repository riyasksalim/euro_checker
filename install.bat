@echo off
call .venv\Scripts\activate
pip install -r requirements.txt
python postinstall.py
python test.py