# -*- coding: utf-8 -*-

from ftplib import FTP
from ftplib import FTP_TLS
import pysftp
import os   
import ssl   
import sys
import time
import math
import datetime
import odoo.addons.decimal_precision as dp

from odoo import tools
from odoo.osv import expression
from odoo.tools.float_utils import float_round as round
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, float_is_zero, float_compare, pycompat
from odoo.exceptions import UserError, ValidationError
from odoo import api, fields, models, _
from odoo.osv import osv

class paramftp(models.Model):
    _name = "iwel.paramftp"
    _description = "Parametres du FTP"

    serveur = fields.Char(string='Serveur FTP')
    user = fields.Char(string='Utilisateur FTP')
    password = fields.Char(string='Mot de passe FTP')
    repiwel = fields.Char(string='Répertoire IWEL')
    repentree = fields.Char(string='Entree des fichiers')
    reparchives = fields.Char(string='Archives des fichiers')
    
class table(models.Model):
    _name = "iwel.table"
    _description = "Tables IWEL"

    def get_nbchamp(self):
        for record in self:
            record.nbchamp = len(self.env['iwel.champ'].search([('idtable','=',record.id)]))
    name = fields.Char(string='Nom')
    table = fields.Char(string='Table')
    mode = fields.Selection([('importer','Importer'),('exporter','Exporter')], 'Mode')
    nb = fields.Integer('Nombre opérations')
    periodicite =  fields.Selection([('jour','Journalier'),('semaine','Hebdomadaire'),('mois','Mensuel'),('trimestre','Trimestriel')], 'Périodicité')
    sequence = fields.Integer('Sequence')
    nbchamp = fields.Integer('Nombre de champs')
    positionref = fields.Integer(string='Position ref unique')
    positionname = fields.Integer(string='Position name')
    champoblig = fields.Text(String='Champs obligatoires')
    valdef = fields.Text(String='Valeurs des champs')
    nbaj = fields.Integer(String='Nombre de champs ajoutés')
    ligne_champs = fields.One2many('iwel.champ','idtable','Champ')

class champ(models.Model):
    _name = "iwel.champ"
    _description = "Champs IWEL"

    idtable = fields.Many2one('iwel.table',string='Table')   
    name = fields.Char(string='Nom')
    numcol = fields.Integer(string='Num Colonne')
    nomcol = fields.Integer(string='Nom Colonne')
    position = fields.Integer(string='Position')
    longueur = fields.Integer(string='Longueur')
    libelle = fields.Char(string='Libellé')
    format = fields.Char(string='Format')
    description = fields.Text(string='Description')
    odoo = fields.Char('Champ ODOO')
    
    
class ProductCategory(models.Model):
    _name = "product.category"
    _inherit = "product.category"

    code = fields.Char('Code catégorie')
    codeparent = fields.Char('Code Parent catégorie')
    frais = fields.Float('Frais(%)')
    coeff = fields.Float('Coeff(%)')
    _sql_constraints = [
      ('codeunique', 'unique(code,codeparent)', 'Existe deja')
     ]
class ProductTemplate(models.Model):
    _name = "product.template"
    _inherit = "product.template"

    @api.depends('ligne_gencod.c1')
    def get_barcode(self):
        for record in self:
            barcode2 = barcode3 = ''
            i = 1
            for recordfil in record.ligne_gencod:
                if i == 1:
                   barcode2 = recordfil.c1
                if i == 2:
                   barcode3 = recordfil.c1
                i = i+1
            record.barcode2 = barcode2
            record.barcode3 = barcode3
    @api.depends('idfamille')
    def get_rayon(self):
        for record in self:
            record.idrayon = record.idfamille.idrayon.c2
    def majprix(self):
        for record in self:
            if record.frais is not None and record.frais != 0 and record.coeff is not None and record.coeff!=0:
               record.standard_price = record.prixbase*(1+record.frais/100)
               record.list_price = record.prixbase*(1+record.frais/100)*record.coeff
    c1 = fields.Char('Date de création')
    c2 = fields.Char('Date de modification')
    c3 = fields.Char('Code article Domaxel')
    refuniq = fields.Char('Code article Domaxel')
    c4 = fields.Char('Code fournisseur Domaxel')
    c5 = fields.Char('Département d\'activité')
    c6 = fields.Char('Référence article fournisseur')
    c7 = fields.Char('Code marque propre')
    c8 = fields.Char('Marque propre')
    c9 = fields.Char('Langue')
    c10 = fields.Char('Libellé caisse')
    c11 = fields.Char('Désignation article')
    c12 = fields.Char('Libellé long')
    c13 = fields.Char('Code TVA')
    c14 = fields.Char('Quantité minimum de commande')
    c15 = fields.Char('Première quantité pour remise')
    c16 = fields.Char('Coefficient de 1ere remise')
    c17 = fields.Char('Deuxième quantité pour remise')
    c18 = fields.Char('Coefficient de 2eme remise')
    c19 = fields.Char('Troisième quantité pour remise')
    c20 = fields.Char('Coefficient de 3eme remise')
    c21 = fields.Char('Unité de prix à la cession')
    c22 = fields.Char('Nombre de sous unité consommateur dans l’article')
    c23 = fields.Char('EAN 13')
    c24 = fields.Char('Code secteur')
    c25 = fields.Char('Code nomenclature Domaxel')
    c26 = fields.Char('Assortiment mini (NIV GAMME)')
    c27 = fields.Char('Assortiment normal (NIV GAMME)')
    c28 = fields.Char('Assortiment élargi (NIV GAMME)')
    c29 = fields.Char('Assortiment complémentaire 1')
    c30 = fields.Char('Assortiment complémentaire 2')
    c31 = fields.Char('Code Etiquette EAN')
    c32 = fields.Char('Image')
    c33 = fields.Char('Code modèle')
    c34 = fields.Char('Unité légale')
    c35 = fields.Char('Mesure de l’article exprimé en unité légale')
    c36 = fields.Char('Pays d’origine ')
    c37 = fields.Char('Poids brut de l’unité de vente')
    c38 = fields.Char('Délai de garantie')
    c39 = fields.Char('Circuit d’approvisionnement')
    c40 = fields.Char('Article permanent')
    c41 = fields.Char('Exclusif à une enseigne')
    c42 = fields.Char('Enseigne')
    c43 = fields.Char('Statut de l’article')
    c44 = fields.Char('Article de substitution')
    c45 = fields.Char('Code Univers')
    c46 = fields.Char('Date visibilité article')
    c47 = fields.Char('Transmission aux adhérents')
    c48 = fields.Char('Ancienne unité de prix')
    c49 = fields.Char('Art à délai de liv. supp')
    c50 = fields.Char('Saison. Non commandable')
    c51 = fields.Char('Filler')
    c52 = fields.Char('Type PSG')
    c53 = fields.Char('Rayon')
    c54 = fields.Char('Famille')
    c55 = fields.Char('Sous-famille')
    c56 = fields.Char('Segment')
    c57 = fields.Char('Sous-segment')
    c58 = fields.Char('Date de fin de vie')
    c59 = fields.Char('Type de remplacement')
    c60 = fields.Char('Code eco produit')
    c61 = fields.Char('Stock non garanti (STKNG)')
    c62 = fields.Char('N° fournisseur réel')
    c63 = fields.Char('Volume')
    c64 = fields.Char('ag.codelmf_generalites à destination du WS OMS')
    idfamille = fields.Many2one('iwel.wnomfam', 'Famille')
    idrayon = fields.Char('Rayon Article', compute='get_rayon', store=True)
    barcode2 = fields.Char('Code barre 2', compute='get_barcode', store=True)
    barcode3 = fields.Char('Code barre 3', compute='get_barcode', store=True)
    prixbase = fields.Float('Prix de base')
    frais = fields.Float('Frais(%)')
    coeff = fields.Float('Coeff(%)')
    list_price = fields.Float(
        'Sales Price', default=1.0,
        digits=dp.get_precision('Product Price'),
        help="Price at which the product is sold to customers.", track_visibility='onchange')
    
    ligne_gencod = fields.One2many('iwel.wgencode','idarticle','gencode')
    ligne_promo = fields.One2many('iwel.wpart','idarticle','promo')
    ligne_promod = fields.One2many('iwel.wpdirect','idarticle','promod')
    ligne_fonc = fields.One2many('iwel.wlibplus','idarticle','fonction')
    ligne_tarif = fields.One2many('iwel.wtarif','idarticle','tarifs')
    _sql_constraints = [
      ('reference unique', 'unique(refuniq)', 'Existe deja')
     ]

class iwel_typesoffres(models.Model):
    _name = "iwel.typesoffres"
    _description = "iwel.typesoffres"

    c1 = fields.Char('Numéro enregistrement')
    c2 = fields.Char('Code offre')
    c3 = fields.Char('Libelle offre')
    c4 = fields.Char('Libelle court offre')
    
class iwel_articlesoffres(models.Model):
    _name = "iwel.articlesoffres"
    _description = "iwel.articlesoffres"

    idarticle = fields.Many2one('product.template','Code article')
    idtype = fields.Many2one('iwel.typesoffres','Type offre')
    c1 = fields.Char('Code article')
    c2 = fields.Char('Code offre')
    
class iwel_wassorti(models.Model):
    _name = "iwel.wassorti"
    _description = "iwel.wassorti"

    c1 = fields.Char('Code assortissement')
    c2 = fields.Char('Libellé assortissement')

class iwel_wassorart(models.Model):
    _name = "iwel.wassorart"
    _description = "Assortissement articles"

    idarticle = fields.Many2one('product.template','Code article')
    c1 = fields.Many2one('Code article')
    c2 = fields.Many2one('iwel.assorti','Code assortissement')
    
class iwel_wassorcli(models.Model):
    _name = "iwel.wassorcli"
    _description = "Assortissement clients"
    
    idassort = fields.Many2one('iwel.assorti','Code assortissement')
    c1 = fields.Char('Code client')
    c2 = fields.Char('Code assortissement')
    
class iwel_wgencode(models.Model):
    _name = "iwel.wgencode"
    _description = "GEN Code"

    c1 = fields.Char('GEN CODE EAN')
    c2 = fields.Char('Code article')
    c3 = fields.Char('Statut')
    idarticle = fields.Many2one('product.template','Article')

class iwel_wlibelleversion(models.Model):
    _name = "iwel.wlibelleversion"
    _description = "Entete de promo"

    c1 = fields.Char('Code Theme Promo')
    c2 = fields.Char('Code Version')
    c3 = fields.Char('Libellé Version')

class iwel_wpart(models.Model):
    _name = "iwel.wpart"
    _description = "Promo article"

    idarticle = fields.Many2one('product.template','Article')
    idtheme = fields.Many2one('iwel.libelleversion','Code Thème promo')
    c1 = fields.Char('Article')
    c2 = fields.Char('Code Thème promo')
    c3 = fields.Char('Nature article')
    c4 = fields.Char('Libellé')
    c5 = fields.Char('Logo de marque')
    c6 = fields.Char('Norme NF')
    c7 = fields.Char('Picto Garantie')
    c8 = fields.Char('Num Page Catalogue')
    c9 = fields.Char('Num version catalogue')
    c10 = fields.Char('Code de désactivation')
    c11 = fields.Char('Quantités préconisées M1')
    c12 = fields.Char('Quantités préconisées M2')
    c13 = fields.Char('Quantités préconisées M3')
    c14 = fields.Char('Minimum vente')
    c15 = fields.Char('Code devise')
    c16 = fields.Char('Prix engagement')
    c17 = fields.Char('Prix Hors engagement')
    c18 = fields.Char('PVI TTC')
    c19 = fields.Char('PVI unité légale')
    c20 = fields.Char('PVI unité légale en Euro')
    c21 = fields.Char('Qté 1 donnant une remise')
    c22 = fields.Char('Coefficient 1 de remise')
    c23 = fields.Char('Qté 2 donnant une remise')
    c24 = fields.Char('Coefficient 2 de remise')
    c25 = fields.Char('Qté 3 donnant une remise')   
    c26 = fields.Char('Coefficient 3 de remise')
    c27 = fields.Char('Prix permanent')
    c28 = fields.Char('col 28')

class iwel_wpdirect(models.Model):
    _name = "iwel.wpdirect"
    _description = "Promo direct"

    idarticle = fields.Many2one('product.template','Article')
    idcollection = fields.Many2one('iwel.wpent','Numero Collection')
    c1 = fields.Char('Numero Collection')
    c2 = fields.Char('Code Article')
    c3 = fields.Many2one('res_partner','Fournisseur')
    c4 = fields.Char('Quantité 1')
    c5 = fields.Char('Prix 1')
    c6 = fields.Char('Quantité 2')
    c7 = fields.Char('Prix 2')
    c8 = fields.Char('Quantité 3')
    c9 = fields.Char('Prix 3')

class iwel_wpent(models.Model):
    _name = "iwel.wpent"
    _description = "Entete promo"

    idtheme = fields.Many2one('iwel.libelleversion','Code Thème promo')
    c1 = fields.Char('Code Thème promo')
    c2 = fields.Char('Libellé')
    c3 = fields.Char('Nature thème')
    c4 = fields.Char('Début prépromo')
    c5 = fields.Char('Pin prépromo')
    c6 = fields.Char('Début Promo')
    c7 = fields.Char('Fin Promo')
    c8 = fields.Char('Début vente magasin')
    c9 = fields.Char('Fin vente magasin')
    c10 = fields.Char('Nombre de livraisons')
    c11 = fields.Char('Date de livraison 1')
    c12 = fields.Char('Date de livraison 2')
    c13 = fields.Char('Date de livraison 3')
    c14 = fields.Char('Date de livraison 4')
    c15 = fields.Char('Date de livraison 5')
    c16 = fields.Char('Date de livraison 6')
    c17 = fields.Char('Tous clients')
    c18 = fields.Char('Condition reglement Eng')
    c19 = fields.Char('Date reglement Eng')
    c20 = fields.Char('Condition reglement Ass')
    c21 = fields.Char('Date reglement Ass')
    c22 = fields.Char('Remise packaging')
    c23 = fields.Char('Num version et page')
    c24 = fields.Char('Gestion du Réassort')
    c25 = fields.Char('Filler')
    c26 = fields.Char('Date règlement1')
    c27 = fields.Char('Date règlement2')
    c28 = fields.Char('Date règlement3')
    c29 = fields.Char('Date règlement4')
    c30 = fields.Char('Date règlement5')
    c31 = fields.Char('Date règlement6')
    c32 = fields.Char('Type promo')
    c33 = fields.Char('col 33')
    
class iwel_wlibplus(models.Model):
    _name = "iwel.wlibplus"
    _description = "Desc fonctionnelle"

    idarticle = fields.Many2one('product.template','Article')
    c1 = fields.Char('Code Article')
    c2 = fields.Char('Code Langue')
    c3 = fields.Char('Num Ligne')
    c4 = fields.Char('Description Fonctionnelle')
    c5 = fields.Char('col 5')


class iwel_wlibtec(models.Model):
    _name = "iwel.wlibtec"
    _description = "Desc technique"

    idarticle = fields.Many2one('product.template','Article')
    c1 = fields.Char('Code article')
    c2 = fields.Char('Code Langue')
    c3 = fields.Char('Num Ligne')
    c4 = fields.Char('Description Technique')

    
class iwel_wmarpro(models.Model):
    _name = "iwel.wmarpro"
    _description = "Marque"

    c1 = fields.Char('Code')
    c2 = fields.Char('Marque')


class iwel_wnomray(models.Model):
    _name = "iwel.wnomray"
    _description = "Rayon"
    _rec_name = "c2"

    def majprix(self):
        for record in self:
            for recordfam in record.ligne_famille:
                for recordart in recordfam.ligne_article:
                    #MAJ FRAIS
                    if recordart.frais == 0:
                       if recordfam.frais == 0:
                          if record.frais != 0: 
                             recordart.standart_price = recordart.prixbase*(1+record.frais/100)
                       else:
                          recordart.standart_price = recordart.prixbase*(1+recordfam.frais/100)
                    else:
                       recordart.standart_price = recordart.prixbase*(1+recordart.frais/100)
                    #MAJ COEFF
                    if recordart.coeff == 0:
                       if recordfam.coeff == 0:
                          if record.coeff != 0: 
                             recordart.list_price = recordart.prixbase*(1+record.frais/100)*(1+record.coeff/100)
                       else:
                          recordart.list_price = recordart.prixbase*(1+recordfam.frais/100)*(1+recordfam.coeff/100)
                    else:
                       recordart.list_price = recordart.prixbase*(1+recordart.frais/100)*(1+recordart.coeff/100)
                    
    c1 = fields.Char('Code')
    c2 = fields.Char('Nom rayon', required=1)
    frais = fields.Float('Frais(%)')
    coeff = fields.Float('Coeff(%)')
    ligne_famille = fields.One2many('iwel.wnomfam','idrayon','Familles')

class iwel_wnomfam(models.Model):
    _name = "iwel.wnomfam"
    _description = "Famille"
    _rec_name = "c3"

    idrayon = fields.Many2one('iwel.wnomray','Rayon')
    c1 = fields.Char('Code Rayon')
    c2 = fields.Char('Code')
    c3 = fields.Char('Nom famille', )
    frais = fields.Float('Frais(%)')
    coeff = fields.Float('Coeff(%)')
    ligne_article = fields.One2many('product.template','idfamille','Articles')

class iwel_wtarif(models.Model):
    _name = "iwel.wtarif"
    _description = "Tarif"

    idarticle = fields.Many2one('product.template','Article')
    c1 = fields.Char('Code article')
    c2 = fields.Char('Zone de prix')
    c3 = fields.Char('Devise prix de base')
    c4 = fields.Char('Prix achat')
    c5 = fields.Char('Devise prix de cession')
    c6 = fields.Char('Prix de cession')
    c7 = fields.Char('PVI TTC')
    c8 = fields.Char('PVI TTC EURO')
    c9 = fields.Char('Date Application')

class iwel_wtarifspec(models.Model):
    _name = "iwel.wtarifspec"
    _description = "Tarif spec"

    idarticle = fields.Many2one('product.template','Article')
    c1 = fields.Char('Code article')
    c2 = fields.Char('Zone de prix')
    c3 = fields.Char('Devise prix de base')
    c4 = fields.Char('Prix achat')
    c5 = fields.Char('Devise prix de cession')
    c6 = fields.Char('Prix de cession')
    c7 = fields.Char('PVI TTC')
    c8 = fields.Char('PVI TTC EURO')
    c9 = fields.Char('Date Application')
    c10 = fields.Char('Code tarif')


class iwel_wtarifspecmq(models.Model):
    _name = "iwel.wtarifspecmq"
    _description = "Tarif spec marque"
    
    c1 = fields.Char('Code contremarque')
    c2 = fields.Char('Code tarif')


class Partner(models.Model):
    _name = "res.partner"
    _inherit = "res.partner"

    c1 = fields.Char('Code fournisseur')
    c2 = fields.Char('Col2')
    c3 = fields.Char('Nom')
    c4 = fields.Char('Raison sociale')
    c5 = fields.Char('col5')
    c6 = fields.Char('Adresse1')
    c7 = fields.Char('Adresse2')
    c8 = fields.Char('Adresse3')
    c9 = fields.Char('Ville')
    c10 = fields.Char('Phone 1')
    c11 = fields.Char('Phone 2')
    c12 = fields.Char('Email')
    c13 = fields.Char('col13')
    c14 = fields.Char('col14')
    c15 = fields.Char('col15')
    c16 = fields.Char('col16')
    c17 = fields.Char('col17')
    c18 = fields.Char('col18')
    c19 = fields.Char('col19')
    c20 = fields.Char('col20')
    c21 = fields.Char('col21')
    c22 = fields.Char('col22')
    c23 = fields.Char('col23')
    refuniq = fields.Char('reference')
    _sql_constraints = [
      ('reference unique', 'unique(refuniq)', 'Existe deja')
     ]
    
class iwel_gestfichier(models.Model):
    _name = "iwel.gestfichier"
    _description = 'Gestion des fichiers'

    def imp_fichierspecial(self):
        idext = self.env['ir.model.data']
        imp = self.env['iwel.table'].search([('mode','=','importer'),('nb','!=','0')])
        for record in imp:
            #fichier = "C:\IWEL\ENTREE\\"+record.name
            fichier = record.name
            cr = open(fichier,"r")
            nbl = 0
            for ligne in cr:
                text = ligne.replace("'"," ").replace("\n","").split(';')
                if record.positionname != 0:
                   text.extend([text[record.positionname],text[record.positionref]])
                else:
                   text.append(text[record.positionref])
                if len(record.valdef) != 0:
                    recup = record.valdef.split(',')
                    text.extend(recup)
                col = []
                for i in range(1,record.nbchamp+1):
                    colname = "c"+str(i)
                    col.append(colname)
                if len(record.champoblig.strip())!=0:
                   recup2 = record.champoblig.split(',')
                   col.extend(recup2)
                colonnes = "("
                inc = 1
                for c in col:
                    if inc == record.nbchamp+record.nbaj:
                       colonnes = colonnes + str(c) + ')'
                    else:
                       colonnes = colonnes + str(c) + ',' 
                    inc = inc + 1
                valeurs = "("
                inc = 1
            
                colonnex = "("
                inc = 1
                for c in col:
                    if inc == record.nbchamp+record.nbaj:
                       colonnex = colonnex + "EXCLUDED."+str(c) + ')'
                    else:
                       colonnex = colonnex + "EXCLUDED."+str(c) + ',' 
                    inc = inc + 1
                valeurs = "("
                inc = 1
                #raise UserError(col) 
                for v in text:
                    if inc == record.nbchamp+record.nbaj:
                       valeurs = valeurs + str(v) + ')'
                    else:
                       valeurs = valeurs + str(v) + ',' 
                    inc = inc + 1  
                requete = "INSERT INTO "+record.table+colonnes+" VALUES"+str(tuple(text))+" ON CONFLICT (refuniq) DO UPDATE SET "+colonnes+"="+colonnex
                nbl = nbl+1
                res = self.env.cr.execute(requete)

    def imp_fichier(self):
        idext = self.env['ir.model.data']
        imp = self.env['iwel.table'].search([('mode','=','importer'),('nb','=','5')])
        for record in imp:
            #fichier = record.name
            fichier = "C:\IWEL\ENTREE\\"+record.name
            cr = open(fichier,"r")
            nbl = 0
            reqdel = "DELETE FROM "+record.table
            res2 = self.env.cr.execute(reqdel)
            for ligne in cr:
                text = ligne.replace("'"," ").replace("\n","").split(';')
                col = []
                for i in range(1,record.nbchamp+1):
                    colname = "c"+str(i)
                    col.append(colname)
                colonnes = "("
                inc = 1
                for c in col:
                    if inc == record.nbchamp+record.nbaj:
                       colonnes = colonnes + str(c) + ')'
                    else:
                       colonnes = colonnes + str(c) + ',' 
                    inc = inc + 1
                valeurs = "("
                inc = 1
                for v in text:
                    if inc == record.nbchamp+record.nbaj:
                       valeurs = valeurs + str(v) + ')'
                    else:
                       valeurs = valeurs + str(v) + ',' 
                    inc = inc + 1
                requete = "INSERT INTO "+record.table+colonnes+" VALUES"+str(tuple(text))
                nbl = nbl+1
                res1 = self.env.cr.execute(requete)
        self.majtable()
    def majtable(self):
        req1 = "UPDATE iwel_wgencode A SET idarticle = P.id FROM product_template P WHERE A.c2 = P.c3"
        req2 = "UPDATE iwel_wpart A SET idarticle = P.id FROM product_template P WHERE A.c1 = P.c3"
        req3 = "UPDATE iwel_wpdirect A SET idarticle = P.id FROM product_template P WHERE A.c2 = P.c3"
        req4 = "UPDATE iwel_wlibplus A SET idarticle = P.id FROM product_template P WHERE A.c1 = P.c3"
        req5 = "UPDATE iwel_wtarif A SET idarticle = P.id FROM product_template P WHERE A.c1 = P.c3"
        req6 = "UPDATE product_template SET default_code = c3 where c3 is not null"
        req7 = "UPDATE product_product p SET barcode = t.c23 FROM product_template t where p.product_tmpl_id=t.id and t.c23 is not null"
        req8 = "UPDATE product_template SET weight = c37::float where c37 is not null"
        req9 = "UPDATE product_template SET volume = c63::float where c63 is not null"
        req10 = "UPDATE iwel_wnomfam f SET idrayon = r.id FROM iwel_wnomray r WHERE f.c1 = r.c1"
        req11 = "UPDATE product_template p SET idfamille = f.id FROM iwel_wnomfam f WHERE p.c54 = f.c2 AND idfamille is null"
        req12 = "UPDATE product_template p SET prixbase = t.c8::float FROM iwel_wtarif t WHERE t.idarticle = p.id and prixbase is null"
        req13 = "update product_template set sale_line_warn = 'no-message' where sale_line_warn = '1'"
        req14 = "update product_template set purchase_line_warn = 'no-message' where purchase_line_warn = '1'"
        req15 = "update product_template set tracking = 'none' where tracking = '1'"
        self.env.cr.execute(req1)
        self.env.cr.execute(req2)
        self.env.cr.execute(req3)
        self.env.cr.execute(req4)
        self.env.cr.execute(req5)
        self.env.cr.execute(req6)
        self.env.cr.execute(req7)
        self.env.cr.execute(req8)
        self.env.cr.execute(req9)
        self.env.cr.execute(req10)
        self.env.cr.execute(req11)
        self.env.cr.execute(req12)
        self.env.cr.execute(req13)
        self.env.cr.execute(req14)
        self.env.cr.execute(req15)
    name = fields.Char('reference')

    def reception(self):
        repentree = "/home/odoo/iwel/entree"
        repentreeserv = "C:\IWEL\TEST"
        reparchiveserv = "/home/brico/archives"
        cnopts = pysftp.CnOpts()
        cnopts.hostkeys = None 
        with pysftp.Connection('37.139.19.239', username='brico', password='brico', cnopts=cnopts) as sftp:
           with sftp.cd('C:\IWEL\TEST'):           # temporarily chdir to allcode
                os.chdir(repentree)
                fichiers = [f for f in sftp.listdir() if f!="." and f!=".."]
                for fichier in fichiers:
                    nomfichier = repentreeserv+"/"+fichier
                    nomarchive = reparchiveserv+"/"+fichier
                    sftp.get(nomfichier)         # get a remote file
                    sftp.rename(nomfichier,nomarchive)
