
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
    init_map();
});

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

    var map = L.map('map', {
        center: new L.LatLng(46.603354, 10),
        zoom: 4,
        layers: [mapquest]
    });
    map.attributionControl.setPrefix('');
    L.control.layers({'MapQuest': mapquest, 'OSM Mapnik': osm, 'MapQuest Aerial': mapquestsat}).addTo(map);
    map.on('baselayerchange', function(a) {
        if(a.name == 'MapQuest Aerial') {
            map.addLayer(hyb);
            hyb.bringToFront();
        } else {
            map.removeLayer(hyb);
        }
    });
}

function change_input_num(li, new_num, reset=false) {
    li.find('input,select').each(function() {
        var id = $(this).attr('id').replace(/^(.*)-\d{1,4}/, '$1-'+new_num);
        $(this).attr({'name': id, 'id': id});
        if(reset)
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
    change_input_num(new_element, elem_num, true);
    new_element.children('button').remove();
    new_element.children('.help-inline.error-list').remove();
    new_element.find('.bootstrap-select').remove();
    append_remove_button(new_element);
    new_element.find('.selectpicker').data('selectpicker', null).selectpicker();
    el.after(new_element);
}
