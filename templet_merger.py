from qgis.PyQt.QtWidgets import QAction, QMessageBox
from qgis.core import (
    QgsProject, QgsField, edit
)
from qgis import processing

class TempletMerger:
    def __init__(self, iface):
        self.iface = iface
        self.action = None

    def initGui(self):
        self.action = QAction("Templet Merger", self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        self.iface.addPluginToMenu("&Templet Merger", self.action)

    def unload(self):
        self.iface.removePluginMenu("&Templet Merger", self.action)

    def run(self):
        layer = self.iface.activeLayer()
        if not layer:
            QMessageBox.critical(None, "Error", "No active layer selected.")
            return

        template_layer = None
        for lyr in QgsProject.instance().mapLayers().values():
            if lyr.name() == "TEMPLATE_NEW":
                template_layer = lyr
                break
        if not template_layer:
            QMessageBox.critical(None, "Error", "TEMPLATE_NEW file not added")
            return

        if "Name" not in [f.name() for f in layer.fields()]:
            QMessageBox.critical(None, "Error", "No 'Name' column found in input layer.")
            return

        expr = 'substr("Name",0,-4)'
        updated_layer = processing.run("qgis:fieldcalculator", {
            'INPUT': layer,
            'FIELD_NAME': 'Name',
            'FIELD_TYPE': 2,
            'FIELD_LENGTH': 255,
            'NEW_FIELD': False,
            'FORMULA': expr,
            'OUTPUT': 'memory:'
        })['OUTPUT']

        for f in updated_layer.getFeatures():
            if len(f["Name"]) != 15:
                QMessageBox.critical(None, "Error", "name column length not matched")
                return

        keep_fields = ["fid", "Name", "Title", "Path"]
        drop_fields = [f.name() for f in updated_layer.fields() if f.name() not in keep_fields]
        cleaned = processing.run("qgis:deletecolumn", {
            'INPUT': updated_layer,
            'COLUMN': drop_fields,
            'OUTPUT': 'memory:'
        })['OUTPUT']

        merged = processing.run("qgis:mergevectorlayers", {
            'LAYERS': [cleaned, template_layer],
            'OUTPUT': 'memory:merged with templete'
        })['OUTPUT']

        if "PHOTO_ID" not in [f.name() for f in merged.fields()]:
            merged.dataProvider().addAttributes([QgsField("PHOTO_ID", 10)])
            merged.updateFields()

        with edit(merged):
            for f in merged.getFeatures():
                f["PHOTO_ID"] = f["Name"]
                merged.updateFeature(f)

        drop_cols = [c for c in ["Name", "layer"] if c in [f.name() for f in merged.fields()]]
        if drop_cols:
            merged = processing.run("qgis:deletecolumn", {
                'INPUT': merged,
                'COLUMN': drop_cols,
                'OUTPUT': 'memory:'
            })['OUTPUT']

        QgsProject.instance().addMapLayer(merged)
        QMessageBox.information(None, "Success", "Layer created: merged with templete")
