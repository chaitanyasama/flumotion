# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4
#
# Flumotion - a streaming media server
# Copyright (C) 2008 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# This file may be distributed and/or modified under the terms of
# the GNU General Public License version 2 as published by
# the Free Software Foundation.
# This file is distributed without any warranty; without even the implied
# warranty of merchantability or fitness for a particular purpose.
# See "LICENSE.GPL" in the source distribution for more information.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

import gettext
import os

from flumotion.common import errors
from flumotion.common.messages import N_, gettexter, Info
from flumotion.common.python import sorted
from flumotion.wizard.basesteps import VideoSourceStep

__version__ = "$Rev$"
_ = gettext.gettext
T_ = gettexter('flumotion')


class WebcamStep(VideoSourceStep):
    name = _('Webcam')
    glade_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              'webcam-wizard.glade')
    component_type = 'video4linux'
    icon = 'webcam.png'

    def __init__(self, wizard, model):
        VideoSourceStep.__init__(self, wizard, model)
        self._in_setup = False
        # _sizes is probed, not set from the UI
        self._sizes = None

    # WizardStep

    def setup(self):
        self._in_setup = True
        self.device.data_type = str
        self.framerate.data_type = object

        self.device.prefill(['/dev/video0',
                             '/dev/video1',
                             '/dev/video2',
                             '/dev/video3'])

        self.model.properties.device = '/dev/video0'

        self.add_proxy(self.model.properties,['device'])

        self._in_setup = False

    def worker_changed(self):
        self.model.worker = self.worker
        self._clear()
        self._run_checks()

    # Private

    def _clear(self):
        self.size.set_sensitive(False)
        self.framerate.set_sensitive(False)
        self.label_name.set_label("")
        self.wizard.block_next(True)

    def _run_checks(self):
        if self._in_setup:
            return None

        self.wizard.block_next(True)

        device = self.device.get_selected()
        msg = Info(T_(
                N_("Probing webcam, this can take a while...")),
            id='webcam-check')
        self.wizard.add_msg(msg)
        d = self.run_in_worker('flumotion.worker.checks.video', 'checkWebcam',
                           device, id='webcam-check')

        def errRemoteRunFailure(failure):
            failure.trap(errors.RemoteRunFailure)
            self.debug('a RemoteRunFailure happened')
            self._clear()

        def errRemoteRunError(failure):
            failure.trap(errors.RemoteRunError)
            self.debug('a RemoteRunError happened')
            self._clear()

        def deviceFound(result):
            if not result:
                self.debug('no device %s' % device)
                self._clear()
                return None

            deviceName, factoryName, sizes = result
            self.model.properties.element_factory = factoryName
            self._populate_sizes(sizes)
            self.wizard.clear_msg('webcam-check')
            self.label_name.set_label(deviceName)
            self.wizard.block_next(False)
            self.size.set_sensitive(True)
            self.framerate.set_sensitive(True)

        d.addCallback(deviceFound)
        d.addErrback(errRemoteRunFailure)
        d.addErrback(errRemoteRunError)

    def _populate_sizes(self, sizes):
        # Set sizes before populating the values, since
        # it trigger size_changed which depends on this
        # to be set
        self._sizes = sizes

        values = []
        for w, h in sorted(sizes.keys(), reverse=True):
            values.append(['%d x %d' % (w, h), (w, h)])
        self.size.prefill(values)

    def _populate_framerates(self, size):
        values = []
        for d in self._sizes[size]:
            num, denom = d['framerate']
            values.append(('%.2f fps' % (1.0*num/denom), d))
        self.framerate.prefill(values)

    def _update_size(self):
        size = self.size.get_selected()
        if size:
            self._populate_framerates(size)
            width, height = size
        else:
            self.warning('something bad happened: no height/width selected?')
            width, height = 320, 240

        self.model.properties.width = width
        self.model.properties.height = height

    def _update_framerate(self):
        if self._in_setup:
            return None

        framerate = self.framerate.get_selected()
        if framerate:
            num, denom = framerate['framerate']
            mime = framerate['mime']
            format = framerate.get('format', None)
        else:
            self.warning('something bad happened: no framerate selected?')
            num, denom = 15, 2
            mime = 'video/x-raw-yuv'
            format = None

        self.model.properties.mime = mime
        self.model.properties.framerate = '%d/%d' % (num, denom)
        if format:
            self.model.properties.format = format

    # Callbacks

    def on_device_changed(self, combo):
        self._run_checks()

    def on_size_changed(self, combo):
        self._update_size()

    def on_framerate_changed(self, combo):
        self._update_framerate()


class WebcamWizardPlugin(object):
    def __init__(self, wizard):
        self.wizard = wizard

    def get_production_step(self, type):
        return WebcamStep
