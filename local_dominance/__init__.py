# -*- coding: utf-8 -*-
"""
/***************************************************************************
 LocalDominance
                                 A QGIS plugin
 This plugin makes Local Dominance visualisations of raster images
                             -------------------
        begin                : 2017-07-31
        copyright            : (C) 2017 by Thomas Ljungberg
        email                : t.ljungberg74@gmail.com
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load LocalDominance class from file LocalDominance.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .local_dominance import LocalDominance
    return LocalDominance(iface)
