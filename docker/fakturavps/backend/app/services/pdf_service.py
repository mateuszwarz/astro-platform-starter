import io
from decimal import Decimal
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, HRFlowable
from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT


def format_currency(value) -> str:
    try:
        val = Decimal(str(value))
        return f"{val:,.2f} PLN".replace(",", " ")
    except:
        return f"{value} PLN"


def format_date(d) -> str:
    if d is None:
        return "-"
    try:
        return d.strftime("%d.%m.%Y")
    except:
        return str(d)


def generate_invoice_pdf(invoice, contractor, items, company, include_cost_type: bool = True) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )

    styles = getSampleStyleSheet()
    style_normal = ParagraphStyle('normal', fontName='Helvetica', fontSize=9, leading=14)
    style_bold = ParagraphStyle('bold', fontName='Helvetica-Bold', fontSize=9, leading=14)
    style_title = ParagraphStyle('title', fontName='Helvetica-Bold', fontSize=16, leading=20, alignment=TA_CENTER)
    style_header = ParagraphStyle('header', fontName='Helvetica-Bold', fontSize=10, leading=14)
    style_small = ParagraphStyle('small', fontName='Helvetica', fontSize=8, leading=12, textColor=colors.grey)
    style_right = ParagraphStyle('right', fontName='Helvetica', fontSize=9, leading=14, alignment=TA_RIGHT)

    elements = []

    invoice_type_labels = {
        "sprzedaz": "FAKTURA VAT",
        "zakup": "FAKTURA ZAKUPOWA",
        "korekta": "FAKTURA KORYGUJĄCA",
        "zaliczkowa": "FAKTURA ZALICZKOWA",
        "proforma": "FAKTURA PRO FORMA",
        "paragon": "PARAGON",
    }
    doc_type = invoice_type_labels.get(invoice.type, "FAKTURA VAT")

    cost_type_label = None
    if include_cost_type and invoice.type == "zakup" and invoice.cost_type:
        cost_type_label = "TOWAR" if invoice.cost_type == "towar" else "USŁUGA"

    elements.append(Paragraph(doc_type, style_title))
    if cost_type_label:
        style_ct = ParagraphStyle(
            'cost_type', fontName='Helvetica-Bold', fontSize=10, leading=14,
            alignment=TA_CENTER, textColor=colors.Color(0.2, 0.4, 0.8)
        )
        elements.append(Paragraph(f"Rodzaj: {cost_type_label}", style_ct))
    elements.append(Paragraph(f"Nr: {invoice.number}", ParagraphStyle('num', fontName='Helvetica-Bold', fontSize=12, leading=16, alignment=TA_CENTER)))
    elements.append(Spacer(1, 0.5*cm))

    company_name = company.name if company else "Nieznana firma"
    company_nip = company.nip if company else "-"
    company_address = company.address if company else "-"
    company_city = f"{company.postal_code or ''} {company.city or ''}".strip() if company else "-"
    company_bank = company.bank_account if company else "-"
    company_email = company.email if company else "-"

    contractor_name = contractor.name if contractor else "Nieznany kontrahent"
    contractor_nip = contractor.nip if contractor else "-"
    contractor_address = contractor.address if contractor else "-"
    contractor_city = f"{contractor.postal_code or ''} {contractor.city or ''}".strip() if contractor else "-"

    parties_data = [
        [Paragraph("<b>SPRZEDAWCA</b>", style_header), Paragraph("<b>NABYWCA</b>", style_header)],
        [Paragraph(company_name, style_bold), Paragraph(contractor_name, style_bold)],
        [Paragraph(f"NIP: {company_nip}", style_normal), Paragraph(f"NIP: {contractor_nip}", style_normal)],
        [Paragraph(company_address, style_normal), Paragraph(contractor_address, style_normal)],
        [Paragraph(company_city, style_normal), Paragraph(contractor_city, style_normal)],
        [Paragraph(f"Email: {company_email}", style_normal), Paragraph("", style_normal)],
    ]

    parties_table = Table(parties_data, colWidths=[8.5*cm, 8.5*cm])
    parties_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(parties_table)
    elements.append(Spacer(1, 0.5*cm))

    dates_data = [
        [Paragraph("<b>Data wystawienia:</b>", style_bold), Paragraph(format_date(invoice.issue_date), style_normal),
         Paragraph("<b>Data sprzedaży:</b>", style_bold), Paragraph(format_date(invoice.sale_date), style_normal)],
        [Paragraph("<b>Termin płatności:</b>", style_bold), Paragraph(format_date(invoice.due_date), style_normal),
         Paragraph("<b>Waluta:</b>", style_bold), Paragraph(invoice.currency or "PLN", style_normal)],
    ]
    dates_table = Table(dates_data, colWidths=[4*cm, 4*cm, 4*cm, 5*cm])
    dates_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(dates_table)
    elements.append(Spacer(1, 0.3*cm))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.darkblue))
    elements.append(Spacer(1, 0.3*cm))

    items_header = ["Lp.", "Nazwa towaru/usługi", "Jm.", "Ilość", "Cena netto", "Stawka VAT", "Netto", "VAT", "Brutto"]
    items_data = [items_header]

    vat_summary = {}
    for idx, item in enumerate(items, 1):
        net = Decimal(str(item.net_amount))
        vat = Decimal(str(item.vat_amount))
        gross = Decimal(str(item.gross_amount))
        vat_rate = item.vat_rate

        row = [
            str(idx),
            item.name,
            item.unit or "szt",
            str(item.quantity),
            format_currency(item.unit_price_net),
            f"{vat_rate}%",
            format_currency(net),
            format_currency(vat),
            format_currency(gross),
        ]
        items_data.append(row)

        if vat_rate not in vat_summary:
            vat_summary[vat_rate] = {"net": Decimal("0"), "vat": Decimal("0"), "gross": Decimal("0")}
        vat_summary[vat_rate]["net"] += net
        vat_summary[vat_rate]["vat"] += vat
        vat_summary[vat_rate]["gross"] += gross

    items_table = Table(items_data, colWidths=[0.8*cm, 5*cm, 1*cm, 1.5*cm, 2.5*cm, 1.8*cm, 2*cm, 2*cm, 2.4*cm])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (1, 1), (1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.Color(0.95, 0.95, 0.98)]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 0.5*cm))

    summary_data = [["Stawka VAT", "Podstawa netto", "Kwota VAT", "Kwota brutto"]]
    for vat_rate, amounts in sorted(vat_summary.items()):
        summary_data.append([
            f"{vat_rate}%",
            format_currency(amounts["net"]),
            format_currency(amounts["vat"]),
            format_currency(amounts["gross"]),
        ])

    total_net = Decimal(str(invoice.net_amount))
    total_vat = Decimal(str(invoice.vat_amount))
    total_gross = Decimal(str(invoice.gross_amount))
    summary_data.append(["RAZEM", format_currency(total_net), format_currency(total_vat), format_currency(total_gross)])

    summary_table = Table(summary_data, colWidths=[3*cm, 5*cm, 5*cm, 5*cm])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, -1), (-1, -1), colors.Color(0.8, 0.9, 1.0)),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(Paragraph("<b>Podsumowanie VAT:</b>", style_header))
    elements.append(Spacer(1, 0.2*cm))
    elements.append(summary_table)
    elements.append(Spacer(1, 0.5*cm))

    pay_info = [
        [Paragraph("<b>Informacje płatności</b>", style_header), ""],
        [Paragraph("Konto bankowe:", style_bold), Paragraph(company_bank, style_normal)],
        [Paragraph("Do zapłaty:", style_bold), Paragraph(format_currency(total_gross), style_bold)],
    ]
    pay_table = Table(pay_info, colWidths=[4*cm, 13*cm])
    pay_table.setStyle(TableStyle([
        ('SPAN', (0, 0), (1, 0)),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.9, 0.9, 0.9)),
    ]))
    elements.append(pay_table)

    if invoice.notes:
        elements.append(Spacer(1, 0.3*cm))
        elements.append(Paragraph(f"<b>Uwagi:</b> {invoice.notes}", style_normal))

    elements.append(Spacer(1, 1*cm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
    elements.append(Spacer(1, 0.2*cm))

    footer_parts = [f"Faktura: {invoice.number}"]
    if invoice.ksef_number:
        footer_parts.append(f"Nr KSeF: {invoice.ksef_number}")
    if invoice.status:
        status_labels = {
            "szkic": "Szkic", "oczekuje": "Oczekuje na płatność",
            "zaplacona": "Zapłacona", "przeterminowana": "Przeterminowana",
            "zaakceptowana_ksef": "Zaakceptowana przez KSeF"
        }
        footer_parts.append(f"Status: {status_labels.get(invoice.status, invoice.status)}")
    elements.append(Paragraph(" | ".join(footer_parts), style_small))

    doc.build(elements)
    return buffer.getvalue()
