'use strict';


$(document).ready(function() {
    createDataTables();

    // Auto focus first input in page.
    var firstInput = $('input[type=text]').first();
    firstInput.focus();
    // Move cursor to the end of the input.
    firstInput.val(firstInput.val());
});

// Manage equipments.
$(document).on('click', '.equipment__add', function(event) {
    event.preventDefault();
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


// Datatables.
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

function createDataTables() {
    var table = $('table.dataTables');
    var columns = [];
    var customFilter = table.data('custom-filter');

    // Loop through all the columns, to be able to hook the 'data-render' parameters to existing functions.
    table.find('th').each(function() {
        var col = {};
        // We can't set the render functions using HTML5 data parameters so we simulate this behavior.
        var renderFunction = $(this).data('render');
        if (renderFunction) {
            col.render = window[renderFunction];
        }
        columns.push(col);
    });

    var dataTableParameters = {
        serverSide: true,
        ajax: {
            url: table.data('ajax-url')
        },
        stateSave: true,
        pageLength: 50,
        lengthChange: false,
        responsive: {
            details: false
        },
        processing: true,
        columns: columns,
        rowCallback: addHrefToDataTablesRows
    };

    if (userLocale !== 'en') {
        dataTableParameters['language'] = dataTablesTranslations[userLocale];
    }

    // If there is a custom filter, change the organization of the special div around the dataTable.
    if (customFilter) {
        dataTableParameters['dom'] = '<"row"<"col-sm-6"<"custom_filter checkbox">><"col-sm-6"f>>\
                                      <"row"<"col-sm-12"tr>>\
                                      <"row"<"col-sm-5"i><"col-sm-7"p>>';
    }

    var initialisedDataTable = table.DataTable(dataTableParameters);

    if (customFilter) {
        var tableContainer = $(initialisedDataTable.table().container());

        // Save the custom filter state with the other dataTables parameters.
        initialisedDataTable.on('stateSaveParams.dt', function(event, settings, data) {
            data.customFilter = !tableContainer.find('.custom_filter__input').is(':checked');
        });

        // Add the custom filter in the div created in the dom command above.
        var filterLabel = table.data('custom-filter-label');
        // noinspection JSUnresolvedFunction
        var tableState = initialisedDataTable.state.loaded();
        var inputIsChecked = (!tableState || !tableState.customFilter) ? ' checked' : '';
        var filterHTML = '<label><input class="custom_filter__input" type="checkbox"' + inputIsChecked + '> ' + filterLabel + '</label>';
        tableContainer.find('.custom_filter').html(filterHTML).css('padding', '10px 0 0 10px');
        initialisedDataTable.state.save();

        // Force a draw of the table when the filter state changes.
        tableContainer.find('.custom_filter__input').change(function() {
            initialisedDataTable.draw();
        });
    }

    // If an ajax call is long, the user can browse before the response is received. As the state is by default
    // saved after reception of the reponse, the state changes can be lost.
    // To prevent this, save the state before making the ajax request.
    table.on('preXhr.dt', function() {
        initialisedDataTable.state.save();
    });
}

//Before table initialization, manage when to send the 'hide' query string.
$(document).on('preInit.dt', function(event, settings) {
    var api = new $.fn.dataTable.Api(settings);
    // noinspection JSUnresolvedFunction
    var state = api.state.loaded();

    // This is the table div.
    var table = $(event.target);

    var customFilter = table.data('custom-filter');
    if (customFilter) {
        settings.ajax.data = function(data) {
            // This is the HTML node wrapping around the table with the special search, filter, etc.
            var dataTableContainer = $(table.DataTable().table().container());
            var customFilterInput = dataTableContainer.find('.custom_filter__input');

            // Either visual filter has arrived and we use it, or it's the first load and we use the active storage.
            if ((customFilterInput.length && !customFilterInput.is(':checked')) || (!customFilterInput.length && state && state.customFilter)) {
                data.filter = customFilter;
            }
        };
    }
});

// Add on each row the link sent from the Webservices.
function addHrefToDataTablesRows(row, data) {
    if (data.links) {
        var object_link = jQuery.grep(data.links, function(n) {return n.rel === 'self';});
        var rowTd = $(row).find('td');

        rowTd.each(function() {
            if (!$(this).html()) {
                $(this).html('&nbsp;');
            }
            $(this).wrapInner('<a href="' + object_link[0].href + '"></a>');
        });
    }
}

$(document).on('click', '.paginate_button', function() {
    $('body').animate({scrollTop: 0}, 'slow');
});

// Hide events.
$(document).on('click', '.event__delete', function() {
    const eventID = $(this).data('eventid');
    $('form').append('<input type="hidden" name="event-removed" value="' + eventID + '">');
    $(this).parent().hide('fast');
});

// Validate date format.
$(document).on('submit', 'form', function(event) {
    $('input[type="date"]').each(function() {
        const date = $(this).val();
        if (!date) {
            return true;
        }

        const isHumanDate = date.match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
        if (isHumanDate) {
            $(this).val(isHumanDate[3] + '-' + isHumanDate[2] + '-' + isHumanDate[1]);
            return true;
        }

        const isStandardDate = date.match(/^\d{4}-\d{2}-\d{2}$/);
        if (!isStandardDate) {
            event.preventDefault();
            $(this).val('');
            $(this).parent().addClass('has-error');
            alert('Invalid date format.');
            return false;
        }
    });
});