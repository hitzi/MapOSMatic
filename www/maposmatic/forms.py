# coding: utf-8

# maposmatic, the web front-end of the MapOSMatic city map generation system
# Copyright (C) 2009  David Decotigny
# Copyright (C) 2009  Frédéric Lehobey
# Copyright (C) 2009  Pierre Mauduit
# Copyright (C) 2009  David Mentré
# Copyright (C) 2009  Maxime Petazzoni
# Copyright (C) 2009  Thomas Petazzoni
# Copyright (C) 2009  Gaël Utard

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Forms for MapOSMatic

from django import forms
from django.utils.translation import ugettext_lazy as _

from ocitysmap.coords import BoundingBox as OCMBoundingBox
from www.maposmatic import helpers, models, widgets
import www.settings

class MapSearchForm(forms.Form):
    """
    The map search form, allowing search through the rendered maps.
    """

    query = forms.CharField(min_length=1, required=True)

class MapRenderingJobForm(forms.ModelForm):
    """
    The main map rendering form, displayed on the 'Create Map' page. It's a
    ModelForm based on the MapRenderingJob model.
    """

    class Meta:
        model = models.MapRenderingJob
        fields = ('maptitle', 'administrative_city',
                  'lat_upper_left', 'lon_upper_left',
                  'lat_bottom_right', 'lon_bottom_right')

    MODES = (('admin', _('Administrative boundary')),
             ('bbox', _('Bounding box')))

    mode = forms.ChoiceField(choices=MODES, initial='admin',
                             widget=forms.RadioSelect)
    maptitle = forms.CharField(max_length=256, required=False)
    bbox = widgets.AreaField(label=_("Area"),
                             fields=(forms.FloatField(), forms.FloatField(),
                                     forms.FloatField(), forms.FloatField()))
    map_language = forms.ChoiceField(choices=www.settings.MAP_LANGUAGES,
                                     widget=forms.Select(
                                        attrs={'style': 'min-width: 200px'}))
    administrative_osmid = forms.IntegerField(widget=forms.HiddenInput,
                                              required=False)

    def clean(self):
        """Cleanup function for the map query form. Different checks are
        required depending on the selected mode (by admininstrative city, or by
        bounding box).

        Returns the cleaned_data array.
        """

        cleaned_data = self.cleaned_data

        mode = cleaned_data.get("mode")
        city = cleaned_data.get("administrative_city")
        title = cleaned_data.get("maptitle")

        if mode == 'admin':
            if city == "":
                msg = _(u"Administrative city required")
                self._errors["administrative_city"] = forms.util.ErrorList([msg])
                del cleaned_data["administrative_city"]

            # No choice, the map title is always the name of the city
            cleaned_data["maptitle"] = city

            # Make sure that bbox and admin modes are exclusive
            cleaned_data["lat_upper_left"] = None
            cleaned_data["lon_upper_left"] = None
            cleaned_data["lat_bottom_right"] = None
            cleaned_data["lon_bottom_right"] = None

            try:
                helpers.check_osm_id(cleaned_data.get("administrative_osmid"))
            except Exception,ex:
                msg = _(u"Error with osm city: %s" % ex)
                self._errors['administrative_osmid'] = forms.util.ErrorList([msg])

        elif mode == 'bbox':
            if title == '':
                msg = _(u"Map title required")
                self._errors["maptitle"] = forms.util.ErrorList([msg])
                del cleaned_data["maptitle"]

            for f in [ "lat_upper_left", "lon_upper_left",
                       "lat_bottom_right", "lon_bottom_right" ]:
                val = cleaned_data.get(f)
                if val is None:
                    msg = _(u"Required")
                    self._errors['bbox'] = forms.util.ErrorList([msg])
                    del cleaned_data[f]

            # Make sure that bbox and admin modes are exclusive
            cleaned_data["administrative_city"] = ''
            cleaned_data["administrative_osmid"] = None

            # Don't try to instanciate a bounding box with empty coordinates
            if self._errors:
                return cleaned_data
                
            lat_upper_left = cleaned_data.get("lat_upper_left")
            lon_upper_left = cleaned_data.get("lon_upper_left")
            lat_bottom_right = cleaned_data.get("lat_bottom_right")
            lon_bottom_right = cleaned_data.get("lon_bottom_right")

            boundingbox = OCMBoundingBox(lat_upper_left,
                                         lon_upper_left,
                                         lat_bottom_right,
                                         lon_bottom_right)
            (metric_size_lat, metric_size_long) = boundingbox.spheric_sizes()
            if (metric_size_lat > www.settings.BBOX_MAXIMUM_LENGTH_IN_METERS
                or metric_size_long > www.settings.BBOX_MAXIMUM_LENGTH_IN_METERS):
                msg = _(u"Bounding Box too large")
                self._errors['bbox'] = forms.util.ErrorList([msg])

        return cleaned_data

class MapRecreateForm(forms.Form):
    """
    The map recreate form, to reschedule an already processed job on the queue.
    """

    jobid = forms.IntegerField(widget=forms.HiddenInput, required=True)

    def clean(self):
        cleaned_data = self.cleaned_data

        try:
            cleaned_data["jobid"] = int(cleaned_data.get("jobid", 0))
        except ValueError:
            cleaned_data["jobid"] = 0

        return cleaned_data

class MapCancelForm(forms.Form):
    """
    The map cancel form, to cancel a job (when the user has the matching
    nonce).
    """

    jobid = forms.IntegerField(widget=forms.HiddenInput, required=True)
    jobnonce = forms.CharField(widget=forms.HiddenInput, required=True)

    def clean(self):
        cleaned_data = self.cleaned_data

        try:
            cleaned_data["jobid"] = int(cleaned_data.get("jobid", 0))
        except ValueError:
            cleaned_data["jobid"] = 0

        return cleaned_data
