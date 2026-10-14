{
    "name": "Profit & Cashflow Guardian",
    "version": "19.0.1.0.0",
    "category": "Accounting",
    "summary": "AI financial operations guardian",
    "description": """
Profit & Cashflow Guardian

AI-powered financial operations assistant that:
- Detects overdue invoices
- Predicts payment risks
- Forecasts cash shortages
- Monitors profitability
- Generates financial recommendations
    """,

    "author": "Infokom",
    "license": "LGPL-3",

    "depends": [
        "base",
        "account",
    ],

    "data": [
        "security/ir.model.access.csv",
        "views/financial_analysis_views.xml",
        "views/menus.xml",
    ],

    "installable": True,
    "application": True,
}