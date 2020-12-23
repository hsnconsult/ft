# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'Iwel',
    'version' : '1.1',
    'summary': 'IWEL',
    'sequence': 100,
    'description': """
INTERFACE IWEL
====================
    """,
    'category': 'Accounting',
    'website': 'http://www.hsnconsult.com',
    'depends': ['sale','base','account','account_reports','point_of_sale', 'purchase', 'stock', 'sale_stock'],
    'data': [
    'security/iwel_security.xml',
    'security/ir.model.access.csv',
    'views/iwel_view.xml',
    'views/comliv_view.xml',
    'views/amelioration_views.xml',
    'reports/report_etiquette.xml',
    'reports/report_etiquettel.xml',
    'reports/report_reception.xml',
    'reports/report_commande.xml',
    'reports/report_facture.xml',
    'reports/report.xml',
        ],
    'installable': True,
    'application': True,
    'auto_install': False
}
