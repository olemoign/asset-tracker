'use strict';


//Manage equipments
$(document).on('click', '.equipment__add', function() {
    $(this).parent().next().clone()
        .find('select').val('').end()
        .find('input').val('').end()
        .appendTo($(this).parents().eq(1));
});

$(document).on('click', '.equipment__remove', function() {
    if ($('.equipment__block').size() > 1) {
        $(this).parents('.equipment__block').remove();
    } else {
        $(this).parents('.equipment__block')
        .find('[name="asset-equipment-family"]').val('').end()
        .find('[name="asset-equipment-serial_number"]').val('').focus();
    }
});


//Datatables
var dataTablesTranslations = {
    'fr': {
        'sProcessing':     'Traitement en cours...',
        'sSearch':         'Rechercher&nbsp;:',
        'sLengthMenu':     'Afficher _MENU_ &eacute;l&eacute;ments',
        'sInfo':           'Affichage de l\'&eacute;l&eacute;ment _START_ &agrave; _END_ sur _TOTAL_ &eacute;l&eacute;ments',
        'sInfoEmpty':      'Affichage de l\'&eacute;l&eacute;ment 0 &agrave; 0 sur 0 &eacute;l&eacute;ments',
        'sInfoFiltered':   '(filtr&eacute; de _MAX_ &eacute;l&eacute;ments au total)',
        'sInfoPostFix':    '',
        'sLoadingRecords': 'Chargement en cours...',
        'sZeroRecords':    'Aucun &eacute;l&eacute;ment &agrave; afficher',
        'sEmptyTable':     'Aucune donn&eacute;e disponible dans le tableau',
        'oPaginate': {
            'sFirst':      'Premier',
            'sPrevious':   'Pr&eacute;c&eacute;dent',
            'sNext':       'Suivant',
            'sLast':       'Dernier'
        },
        'oAria': {
            'sSortAscending':  ': activer pour trier la colonne par ordre croissant',
            'sSortDescending': ': activer pour trier la colonne par ordre d&eacute;croissant'
        }
    }
};

$(document).ready(function() {
    var favicon_link = $('link[rel=icon]');
    var favicon = favicon_link.css('backgroundImage').match(/\((.*?)\)/)[1].replace(/('|")/g,'');
    favicon_link.attr('href', favicon);

    var dataTableParameters = {
        'serverSide': true,
        'stateSave': true,
        'pageLength': 50,
        'lengthChange': false,
        'rowCallback': addHrefToDataTablesRows
    };

    if (userLocale !== 'en') {
        dataTableParameters['language'] = dataTablesTranslations[userLocale];
    }

    $('table.dataTables').DataTable(dataTableParameters);
});

function addHrefToDataTablesRows(row, data) {
    var object_link = jQuery.grep(data.links, function(n) {return n.rel == 'self';});
    row.setAttribute('data-href', object_link[0].href);
}

$(document).on('click', 'table tr', function() {
    if (this.hasAttribute('data-href')) {
        window.location.href = this.getAttribute('data-href');
    }
});