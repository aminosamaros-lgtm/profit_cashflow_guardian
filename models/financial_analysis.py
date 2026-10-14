import requests
from odoo import models, fields
from odoo.exceptions import UserError


class FinancialAnalysis(models.Model):
    _name = "profit.cashflow.analysis"
    _description = "Profit & Cashflow Financial Analysis"
    _order = "create_date desc"

    name = fields.Char(string="Analysis", required=True, default="Financial Analysis")
    state = fields.Selection(
        [("draft", "Draft"), ("done", "Done")], default="draft")

    total_revenue = fields.Monetary(string="Total Revenue", currency_field="currency_id")
    total_expenses = fields.Monetary(string="Total Expenses", currency_field="currency_id")
    profit = fields.Monetary(string="Profit", currency_field="currency_id")
    outstanding_amount = fields.Monetary(string="Outstanding Receivables", currency_field="currency_id")
    overdue_amount = fields.Monetary(string="Overdue Amount", currency_field="currency_id")
    cash_forecast = fields.Monetary(string="Cash Forecast", currency_field="currency_id")
    payment_risk = fields.Float(string="Payment Risk (%)")

    risk_level = fields.Selection(
        [("low", "Low"), ("medium", "Medium"), ("high", "High")],
        string="AI Risk Level")
    summary = fields.Text(string="AI Summary")
    reminders = fields.Text(string="Suggested Reminders")

    currency_id = fields.Many2one(
        "res.currency", string="Currency",
        default=lambda self: self.env.company.currency_id.id, required=True)

    def _compute_figures(self):
        """Calcule les montants à partir des factures Odoo."""
        Move = self.env["account.move"]
        today = fields.Date.today()
        posted = [("state", "=", "posted"), ("company_id", "=", self.env.company.id)]

        customer = Move.search(posted + [("move_type", "=", "out_invoice")])
        vendor = Move.search(posted + [("move_type", "=", "in_invoice")])
        unpaid = customer.filtered(lambda m: m.payment_state in ("not_paid", "partial"))
        overdue = unpaid.filtered(lambda m: m.invoice_date_due and m.invoice_date_due < today)
        vendor_unpaid = vendor.filtered(lambda m: m.payment_state in ("not_paid", "partial"))

        revenue = sum(abs(m.amount_total_signed) for m in customer)
        expenses = sum(abs(m.amount_total_signed) for m in vendor)
        outstanding = sum(abs(m.amount_residual_signed) for m in unpaid)
        overdue_amt = sum(abs(m.amount_residual_signed) for m in overdue)
        to_pay = sum(abs(m.amount_residual_signed) for m in vendor_unpaid)

        self.write({
            "total_revenue": revenue,
            "total_expenses": expenses,
            "profit": revenue - expenses,
            "outstanding_amount": outstanding,
            "overdue_amount": overdue_amt,
            "cash_forecast": outstanding - to_pay,
            "payment_risk": (overdue_amt / outstanding * 100) if outstanding else 0.0,
        })
        return unpaid

    def action_analyze(self):
        self.ensure_one()
        url = self.env["ir.config_parameter"].sudo().get_param("guardian.n8n_url")
        if not url:
            raise UserError("Paramètre système 'guardian.n8n_url' manquant.")

        unpaid = self._compute_figures()
        if not unpaid:
            raise UserError("Aucune facture client impayée à analyser.")

        today = fields.Date.today()
        payload = {
            "invoices": [{
                "number": m.name,
                "customer": m.partner_id.name,
                "amount_due": m.amount_residual,
                "due_date": str(m.invoice_date_due),
                "overdue": bool(m.invoice_date_due and m.invoice_date_due < today),
            } for m in unpaid],
        }
        try:
            r = requests.post(url, json=payload, timeout=120)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            raise UserError("Erreur n8n : %s" % e)

        self.write({
            "risk_level": data.get("risk_level"),
            "summary": data.get("summary"),
            "reminders": data.get("reminders"),
            "state": "done",
        })