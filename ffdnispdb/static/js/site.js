
"use strict";

$(function () {
    $('.fieldlist').each(function() {
        var $this=$(this);
        var lis=$this.children('li');
        lis.first().children(':first').after(' <button class="btn btn-mini" type="button"><i class="icon-plus"></i></button>');
        lis.first().children('button').click(function() {
            clone_fieldlist($this.children('li:last'));
        });
        lis=lis.slice(1);
        lis.each(function() {
            append_remove_button($(this));
        });
    });
    $('.selectpicker').selectpicker();
    $("[rel=tooltip]").tooltip();

    var Geoinput = function(el, options, e) {
        this.$element = $(el);
        this.init();
    };
    Geoinput.prototype = {
        constructor: Geoinput,

        init: function() {
            this.$element.hide();
            this.$button = this.makeButton();
            this.$modal  = this.makeModal();
            this.$element.after(this.$button);
            this.$element.after(this.$modal);

            this.$modal.find('textarea').val(this.$element.val());
            this.buttonIcon();

            var that = this;
            this.$button.click(function(e) {
                e.preventDefault();
                that.$modal.modal();
                return false;
            });
            this.$modal.find('.btn-primary').click(function(e) {
                e.preventDefault();
                that.$modal.modal('hide');
                that.$element.val(that.$modal.find('textarea').val());
                that.buttonIcon.call(that);
                return false;
            });
        },

        buttonIcon: function() {
            if(this.$element.val())
                this.$button[0].firstChild.src = '/static/img/map_edit.png';
            else
                this.$button[0].firstChild.src = '/static/img/map.png';
        },

        makeButton: function() {
            return $('<button/>').addClass("btn btn-default geoinput-button")
                                 .css('padding', '4px 7px')
                                 .attr('title', 'enter geojson')
                                 .html('<img src="/static/img/map.png" alt="map">');
        },

        makeModal: function() {
            return $('<div class="modal hide geoinput-modal">'+
                     '<div class="modal-header">'+
                     '<h3>GeoJSON Input</h3>'+
                     '</div>'+
                     '<div class="modal-body">'+
                     '<p>Paste your GeoJSON here:</p>'+
                     '<textarea style="width: 97%; height: 200px"></textarea>'+
                     '</div>'+
                     '<div class="modal-footer">'+
                     '<button class="btn" data-dismiss="modal" aria-hidden="true">Cancel</button>'+
                     '<button class="btn btn-primary">Done</button>'+
                     '</div>'+
                     '</div>')
        }
    }

    $.fn.geoinput = function(options, event) {
        return this.each(function() {
            var $this = $(this), data = $this.data('geoinput');
            if($this.is('input, textarea')) {
                $this.data('geoinput', (data = new Geoinput(this, options, event)));
            }
        });
    };
    $('.geoinput').geoinput();
    init_map();
});

function layer_from_covered_area(ca) {
    return L.geoJson(ca['area'], {
        style: {
            "color": "#ff7800",
            "weight": 5,
            "opacity": 0.65
        }
    });
}

function get_covered_areas(isp_id, cb) {
    if('areas' in window.isp_list[isp_id]) {
        cb(window.isp_list[isp_id]['areas']);
        return;
    } else {
        window.isp_list[isp_id]['areas']=[];
    }

    return $.getJSON('/isp/'+isp_id+'/covered_areas.json', function done(data) {
        $.each(data, function(k, covered_area) {
            if(!covered_area['area'])
                return;
            covered_area['layer']=layer_from_covered_area(covered_area);
            window.isp_list[isp_id]['areas'].push(
                covered_area
            );
        });
        cb(window.isp_list[isp_id]['areas']);
    });
}


L.Control.Pinpoint = L.Control.extend({
    options: {
        position: 'topleft'
    },

    onAdd: function(map) {
        this._map = map;
        this.select_mode = false;
        this._container = L.DomUtil.create('div', 'leaflet-control-pinpoint leaflet-bar');

        this._button = L.DomUtil.create('a', 'leaflet-control-pinpoint-button', this._container);
        this._button.href = '#';
        this._button.innerHTML = '<i class="icon-hand-down"></i>';
        this._button.style = 'cursor: pointer';
        this._button.title = 'Find ISPs near you';
        L.DomEvent
         .addListener(this._button, 'click', L.DomEvent.stop)
         .addListener(this._button, 'click', L.DomEvent.stopPropagation)
         .addListener(this._button, 'click', function() {
            if(this.select_mode) {
                this._map.removeLayer(this._marker);
                this._disableSelect();
            } else {
                this._enableSelect();
            }
        }, this);

        this._icon = L.icon({
            iconUrl: 'static/img/marker_selector.png',
            iconSize:     [18, 28],
            iconAnchor:   [9, 26],
        });
        this._marker = L.marker([0, 0], {icon: this._icon, draggable: true});
        this._marker.on('dragend', this.findNearISP, this);

        return this._container;
    },

    _enableSelect: function() {
        this._marker.addTo(this._map);
        this._map.on('mousemove', this._mouseMove, this);
        this._map.on('click', this._setMarker, this);
        this._map._container.style.cursor = 'crosshair';
        this._marker._icon.style.cursor = 'crosshair';
        this.select_mode = true;
    },

    _disableSelect: function() {
        this._map.off('mousemove', this._mouseMove, this);
        this._map.off('click', this._setMarker, this);
        this._map._container.style.cursor = 'default';
        if(!!this._marker._icon)
            this._marker._icon.style.cursor = 'default';
        this.select_mode = false;
    },

    _mouseMove: function(e) {
        this._marker.setLatLng(e.latlng);
    },

    _setMarker: function(e) {
        this._disableSelect();
        this.findNearISP();
    },

    findNearISP: function() {
        var c=this._marker.getLatLng();
        var map=this._map;
        $.getJSON('/isp/find_near.json?lon='+c.lng+'&lat='+c.lat, function(data) {
            var bnds;
            if(data[0].length) {
                var bnds=new L.LatLngBounds;
                var defered=[];
                $.each(data[0], function(k, match) {
                    var isp=window.isp_list[match['isp_id']];
                    defered.push(get_covered_areas(match['isp_id'], $.noop));
                });
                $.when.apply(this, defered).done(function() {
                    $.each(data[0], function(k, match) {
                        var isp=window.isp_list[match['isp_id']];
                        var ispc=isp['marker'].getLatLng();
                        var matching=null;
                        $.each(isp['areas'], function(j, a) {
                            if(a['id'] == match['area']['id'])
                                matching = a;
                        });
                        bnds.extend([ispc['lat'], ispc['lng']]);
                        isp['marker'].openPopup();
                        if(matching !== null) {
                            bnds.extend(matching['layer'].getBounds());
                            matching['layer'].addTo(map);
                        }
                    });
                    bnds.extend(c);
                    bnds=bnds.pad(0.3);
                    map.fitBounds(bnds, {paddingTopLeft: [20, 20]});
                });
            } else {
                var r=$.map(data[1], function(match, k) {
                    var m=window.isp_list[match['isp_id']]['marker'];
                    var ispc=m.getLatLng();
                    if(k == 0) {
                        map.closePopup();
                        m.openPopup();
                    }

                    return [[ispc.lat, ispc.lng]];
                });
                r.push([c.lat, c.lng])
                bnds=new L.LatLngBounds(r);
                bnds=bnds.pad(0.3);
                map.fitBounds(bnds, {paddingTopLeft: [20, 20]});
            }
        });
    }

})

function init_map() {
    var mapquest=L.tileLayer('http://otile{s}.mqcdn.com/tiles/1.0.0/map/{z}/{x}/{y}.jpg', {
        attribution: '&copy; <a href="http://openstreetmap.org">OpenStreetMap</a> contributors, '+
                     'Tiles courtesy of <a href="http://www.mapquest.com/" target="_blank">MapQuest</a>',
        subdomains: '1234'
    });
    var mapquestsat=L.tileLayer('http://otile{s}.mqcdn.com/tiles/1.0.0/sat/{z}/{x}/{y}.jpg', {
        attribution: '&copy; Tiles courtesy of <a href="http://www.mapquest.com/" target="_blank">MapQuest</a>, '+
                     'Portions Courtesy NASA/JPL-Caltech and U.S. Depart. of Agriculture, Farm Service Agency',
        subdomains: '1234',
        maxZoom: 11
    });
    var osm=L.tileLayer('http://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="http://openstreetmap.org">OpenStreetMap</a> contributors',
        subdomains: 'ab'
    });
    var hyb=L.tileLayer('http://otile{s}.mqcdn.com/tiles/1.0.0/hyb/{z}/{x}/{y}.jpg', {
        subdomains: '1234',
        maxZoom: 11
    });

    if(!$('#map').length)
        return;

    var map = L.map('map', {
        center: new L.LatLng(46.603354, 10),
        zoom: 4,
        minZoom: 2,
        layers: [mapquest],
        worldCopyJump: true
    });
    map.attributionControl.setPrefix('');
    map.addControl(new L.Control.Pinpoint);

    L.control.layers({'MapQuest': mapquest, 'OSM Mapnik': osm, 'MapQuest Aerial': mapquestsat}).addTo(map);
    map.on('baselayerchange', function(a) {
        if(a.name == 'MapQuest Aerial') {
            map.addLayer(hyb);
            hyb.bringToFront();
        } else {
            map.removeLayer(hyb);
        }
    });


    var icon = L.icon({
        iconUrl: 'static/img/marker.png',

        iconSize:     [14, 20], // size of the icon
        iconAnchor:   [7, 20], // point of the icon which will correspond to marker's location
        popupAnchor:  [0, -20] // point from which the popup should open relative to the iconAnchor
    });
    var icon_ffdn = $.extend(true, {}, icon);
    icon_ffdn['options']['iconUrl'] = 'static/img/marker_ffdn.png';

    window.isp_list={};
    $.getJSON('/isp/map_data.json', function(data) {
        $.each(data, function(k, isp) {
            window.isp_list[isp.id]=isp;
            if(!('coordinates' in isp))
                return; // cannot display an ISP without coordinates

            var marker = L.marker([isp['coordinates']['latitude'], isp['coordinates']['longitude']],
                                  {'icon': isp.ffdn_member ? icon_ffdn : icon});

            marker.bindPopup(isp.popup);
            marker.getPopup().on('open', function() {
                get_covered_areas(isp.id, function(items) {
                    $.each(items, function(k, ca) {
                        ca['layer'].addTo(map);
                    });
                });
            });
            marker.getPopup().on('close', function() {
                $.each(window.isp_list[isp.id]['areas'], function(k, ca) {
                    map.removeLayer(ca['layer']);
                });
            });
            marker.addTo(map);
            window.isp_list[isp.id]['marker']=marker;
        });
    });
}

function change_input_num(li, new_num, reset) {
    li.find('input,select,textarea').each(function() {
        var id = $(this).attr('id').replace(/^(.*)-\d{1,4}/, '$1-'+new_num);
        $(this).attr({'name': id, 'id': id});
        if(!!reset)
            $(this).val('').removeAttr('checked');
    });
}

function append_remove_button(li) {
    li.children(':first').after(' <button class="btn btn-mini" type="button"><i class="icon-minus"></i></button>');
    li.children('button').click(function() {
        var ul=li.parent();
        li.remove();
        var i=0;
        ul.children('li').each(function() {
            change_input_num($(this), i);
            i++;
        });
    });
};

function clone_fieldlist(el) {
    var new_element = el.clone(true);
    var elem_id = new_element.find(':input')[0].id;
    var elem_num = parseInt(elem_id.replace(/^.*-(\d{1,4})/, '$1')) + 1;
    new_element.children('button').remove();
    new_element.children('.help-inline.error-list').remove();
    new_element.find('.bootstrap-select').remove();
    new_element.find('.geoinput-button').remove();
    new_element.find('.geoinput-modal').remove();
    change_input_num(new_element, elem_num, true);
    new_element.find('.selectpicker').data('selectpicker', null).selectpicker();
    new_element.find('.geoinput').geoinput();
    append_remove_button(new_element);
    el.after(new_element);
}
