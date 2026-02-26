name: Daily Productivity Report

on:
  schedule:
    # 23:59 Lisboa (WET = UTC+0 no inverno, WEST = UTC+1 no verão)
    # No inverno: 23:59 UTC = 23:59 Lisboa
    # No verão:   22:59 UTC = 23:59 Lisboa
    # Usamos 22:59 UTC para cobrir horário de verão (ajusta para 23:59 no inverno)
    - cron: '59 22 * * *'
  workflow_dispatch: # permite correr manualmente para testar

jobs:
  send-report:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install requests

      - name: Run productivity report
        env:
          MIXPANEL_USERNAME:     ${{ secrets.MIXPANEL_USERNAME }}
          MIXPANEL_SECRET:       ${{ secrets.MIXPANEL_SECRET }}
          MIXPANEL_PROJECT_TOKEN: ${{ secrets.MIXPANEL_PROJECT_TOKEN }}
          GMAIL_USER:            ${{ secrets.GMAIL_USER }}
          GMAIL_APP_PASSWORD:    ${{ secrets.GMAIL_APP_PASSWORD }}
          EMAIL_TO:              ${{ secrets.EMAIL_TO }}
        run: python report.py
