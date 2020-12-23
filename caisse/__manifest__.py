# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'Caisse',
    'version' : '1.1',
    'summary': 'Permet de gérer la caisse',
    'sequence': 180,
    'description': """
Gestion de la paie
====================
    """,
    'license': 'OPL-1',
    'author': 'HSN Consult',
    'category': 'Comptabilité',
    'website': 'http://www.hsnconsult.com',
    'depends': ['point_of_sale', 'hr_holidays', 'paye'],
    'data': [
        'security/caisse_security.xml',
        'views/etats_caisse.xml',
        'views/caisse_view.xml',
        'reports/caisse_report.xml',
        'reports/report_vendeursdet.xml',
        'reports/report_vendeurs.xml',
        'reports/report_rayonsdet.xml',
        'reports/report_stock.xml',
        'reports/report_ventes.xml',
        'reports/report_cloture.xml',
        'reports/report_etiquette.xml',
        ],
    'installable': True,
    'application': True,
    'auto_install': False
}
