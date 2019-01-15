# -*- coding: utf-8 -*-
"""
/***************************************************************************
 LocalDominanceVisualisation
                                 A QGIS plugin
 This plugin makes Local Dominance visualisations of raster images
                              -------------------
        begin                : 2017-07-31
        git sha              : $Format:%H$
        copyright            : (C) 2017 by Thomas Ljungberg
        email                : t.ljungberg74@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
from PyQt4.QtGui import QAction, QIcon, QFileDialog
from qgis.core import QgsMapLayerRegistry, QgsRasterLayer
# Initialize Qt resources from file resources.py
import resources
# Import the code for the dialog
from local_dominance_dialog import LocalDominanceDialog
import os.path
from subprocess import call

class LocalDominance:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'LocalDominance_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)


        # Create the dialog (after translation) and keep reference
        self.dlg = LocalDominanceDialog()


        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Local Dominance Visualisation')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'LocalDominance')
        self.toolbar.setObjectName(u'LocalDominance')
        self.dlg.outFile.clear()
        self.dlg.outFileButton.clicked.connect(self.select_output_file)

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('LocalDominance', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToRasterMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/LocalDominance/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Local Dominance visualisation'),
            callback=self.run,
            parent=self.iface.mainWindow())


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginRasterMenu(
                self.tr(u'&Local Dominance Visualisation'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar


    def select_output_file(self):
        currentLayerIndex = self.dlg.inLayer.currentIndex()
        currentLayer = self.layers[currentLayerIndex]
        currentInFile = currentLayer.dataProvider().dataSourceUri()
        filename = QFileDialog.getSaveFileName(self.dlg, "Output file ", os.path.dirname(currentInFile), '*.tif')
        self.dlg.outFile.setText(filename)


    def run(self):
        """Run method that performs all the real work"""
        self.dlg.inLayer.clear()
        self.layers = [i for i in self.iface.legendInterface().layers() if i.source()[-3:].lower() == 'tif' or i.source()[-4:].lower() == 'tiff']
        layer_list = []
        for layer in self.layers:
            layer_list.append(layer.name())
        self.dlg.inLayer.addItems(layer_list)
        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
              
        # See if OK was pressed
        if result:
                           
            selectedLayerIndex = self.dlg.inLayer.currentIndex()
            selectedLayer = self.layers[selectedLayerIndex]
            f_in = selectedLayer.dataProvider().dataSourceUri()
            argList = [f_in, self.dlg.outFile.text(), str(self.dlg.SR_min.value()),
                       str(self.dlg.SR_max.value()),
                       str(self.dlg.percentageOfPixels.value()), 
                       str(self.dlg.nCores.value())]
            with open(os.path.join(self.plugin_dir, 'argFile.txt'), 'w') as f_out:
                for i in argList:
                    f_out.write(i.encode('utf-8') + '\n')
            
            call(['pythonw.exe', os.path.join(self.plugin_dir, 'local_dominance_parallel.py')], shell=False)


            outRaster = self.dlg.outFile.text()
            layerName = os.path.splitext(os.path.basename(outRaster))
            layer = QgsRasterLayer(outRaster, layerName[0])
            QgsMapLayerRegistry.instance().addMapLayer(layer)

            
            # check default checkboxes
            boxes = [(self.dlg.SRmin_checkBox, 129, '    <number>' + str(self.dlg.SR_min.value()) + '</number>\n'), 
                     (self.dlg.SRmax_checkBox, 158, '    <number>' + str(self.dlg.SR_max.value()) + '</number>\n'), 
                     (self.dlg.Percent_checkBox, 206, '    <number>' + str(self.dlg.percentageOfPixels.value()) + '</number>\n'),
                     (self.dlg.Cores_checkBox, 251, '    <number>' + str(self.dlg.nCores.value()) + '</number>\n')]
            if any([i[0].isChecked() for i in boxes]):
                with open(os.path.join(self.plugin_dir, 'local_dominance_dialog_base.ui'), 'r') as dialogFile:
                    lines = dialogFile.readlines()
                for i in boxes:
                    if i[0]:
                        lines[i[1]] = i[2]
                        
                with open(os.path.join(self.plugin_dir, 'local_dominance_dialog_base.ui'), 'wb') as dialogFile:
                    for l in lines:
                        dialogFile.write(l)
