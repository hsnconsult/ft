# -*- coding: utf-8 -*-

from odoo import models, fields, api


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    idreception = fields.Many2one('iwel.reception', string='reception')

    # def unlink(self):
    #     print('========================>>>>')
    #     for pl in self.order_line:
    #         if pl.idreception:
    #             print("Herrreeee")
    #             pl.idreception.is_invoiced = False
    #     return super(PurchaseOrder, self).unlink()


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    idreception = fields.Many2one('iwel.lignereception', string='Ligne de reception')

    def unlink(self):
        if self.idreception:
            print("Herrreeee")
            self.idreception.is_invoiced = False
        return super(PurchaseOrderLine, self).unlink()
