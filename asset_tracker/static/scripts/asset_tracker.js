'use strict';


$(document).ready(function() {
    createDataTables();

    // Auto focus first input in page.
    const firstInput = $('input[type=text]').first();
    firstInput.focus();
    // Move cursor to the end of the input.
    firstInput.val(firstInput.val());

    // update date format if browser doesn't manage date input types.
    // noinspection JSUnresolvedVariable
    if (!Modernizr.inputtypes.date) {
        $('input[type="date"]').each(function() {
            const date = $(this).val();

            // If date input is empty.
            if (!date) {
                return true;
            }

            // If date is in the format YYYY-MM-DD, transform it in the format DD/MM/YYYY.
            const isStandardDate = date.match(/^(\d{4})-(\d{2})-(\d{2})$/);
            if (isStandardDate) {
                $(this).val(isStandardDate[3] + '/' + isStandardDate[2] + '/' + isStandardDate[1]);
                return true;
            }
        });
    }
});

// Manage equipments.
$(document).on('click', '.equipment__add', function() {
    /**
     * Add a new equipment when the user clicks the '+' sign.
     */
    $('#equipment__reference').clone().removeAttr('id').show().appendTo('#equipment__list');
});

$(document).on('click', '.equipment__remove', function() {
    /**
     * Remove an equipment when the user clicks the 'x' sign.
     */
    $(this).parents('.equipment__block').remove();
});

$(document).on('change', '.equipment__select', function() {
    /**
     * Add expiration dates for Glucometer equipment
     */
    const expiration_date_fields = $(this).parents('.equipment__block').find('.expiration_date_fields');
    const glucometer_family_id = '2YUEMLmH';

    if($(this).val() === glucometer_family_id) {
        expiration_date_fields.show();
    }
    else {
        expiration_date_fields.hide();
        expiration_date_fields.find('input').val('');
    }
});

// Datatables.
const dataTablesTranslations = {
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
    /**
     * Create the dataTable.
     */
    const table = $('table.dataTables');
    if (!table) {
        return
    }

    const columns = [];
    const customFilter = table.data('custom-filter');

    // Loop through all the columns, to be able to hook the 'data-render' parameters to existing functions.
    table.find('th').each(function() {
        const col = {};
        // We can't set the render functions using HTML5 data parameters so we simulate this behavior.
        const renderFunction = $(this).data('render');
        if (renderFunction) {
            col.render = window[renderFunction];
        }
        columns.push(col);
    });

    const dataTableParameters = {
        serverSide: true,
        ajax: {
            url: table.data('ajax-url')
        },
        stateSave: true,
        pageLength: 50,
        lengthChange: false,
        // Remove annoying dataTables responsive behavior when some columns are hidden.
        responsive: {
            details: false
        },
        // Show 'processing' message.
        processing: true,
        columns: columns,
        rowCallback: assetTrackerCallback
    };

    if (userLocale !== 'en') {
        dataTableParameters['language'] = dataTablesTranslations[userLocale];
    }

    // If there is a custom filter, change the organization of the special divs around the dataTable (page size to
    // the bottom).
    if (customFilter) {
        dataTableParameters['dom'] = '<"row"<"col-sm-6"<"custom_filter checkbox">><"col-sm-6"f>>\
                                      <"row"<"col-sm-12"tr>>\
                                      <"row"<"col-sm-5"i><"col-sm-7"p>>';
    }

    const initialisedDataTable = table.DataTable(dataTableParameters);

    // Manage the custom filter.
    if (customFilter) {
        const tableContainer = $(initialisedDataTable.table().container());

        // Save the custom filter state with the other dataTables parameters.
        initialisedDataTable.on('stateSaveParams.dt', function(event, settings, data) {
            data.customFilter = !tableContainer.find('.custom_filter__input').is(':checked');
        });

        // Add the custom filter in the div created in the dom command above.
        const filterLabel = table.data('custom-filter-label');
        const tableState = initialisedDataTable.state.loaded();

        const filterInit = table.data('custom-filter-default') === true;
        // If table didn't yet store state in local storage, take default value, otherwise, use local storage.
        const inputIsChecked = (!tableState && !filterInit) || (tableState && !tableState.customFilter) ? ' checked' : '';

        const filterHTML = '<label><input class="custom_filter__input" type="checkbox"' + inputIsChecked + '> ' + filterLabel + '</label>';
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

$(document).on('preInit.dt', function(event, settings) {
    /**
     * Before dataTable initialization, manage when to send the 'hide' query string for the custon filter.
     */
    const api = new $.fn.dataTable.Api(settings);
    const state = api.state.loaded();

    // This is the table div.
    const table = $(event.target);

    const customFilter = table.data('custom-filter');
    if (customFilter) {
        settings.ajax.data = function(data) {
            // This is the HTML node wrapping around the table with the special search, filter, etc.
            const dataTableContainer = $(table.DataTable().table().container());
            const customFilterInput = dataTableContainer.find('.custom_filter__input');
            const filterInit = table.data('custom-filter-default') === true;

            // 1: the filter checkbox is visible.
            if ((customFilterInput.length && !customFilterInput.is(':checked'))
            // 2: the table isn't visible yet but a filter value is present in the local storage.
            || (!customFilterInput.length && state && state.customFilter)
            // 3: this is the first time we load the table, use the default value.
            || (!customFilterInput.length && !state && filterInit)) {
                data.filter = customFilter;
            }
        };
    }
});

function assetTrackerCallback(row, data) {
    addHref(row, data);
    styleInactiveObjects(row, data);
}

function addHref(row, data) {
    /**
     * Add on each row the link sent from the WebServices.
     */
    if (data.links) {
        const object_link = $.grep(data.links, function(n) {return n.rel === 'self';});
        const rowTd = $(row).find('td');

        rowTd.each(function() {
            // If cell is empty, add a space character so that the cell will be clickable.
            if (!$(this).html()) {
                $(this).html('&nbsp;');
            }
            $(this).wrapInner('<a href="' + object_link[0].href + '"></a>');
        });
    }
}

function styleInactiveObjects(row, data) {
    // noinspection JSUnresolvedVariable
    if (data.hasOwnProperty('is_active') && !data.is_active) {
        $(row).addClass('warning');
    }
}

$(document).on('click', '.paginate_button', function() {
    /**
     * Scroll to top of dataTable when changing page.
     */
    $('body').animate({scrollTop: 0}, 'slow');
});

$(document).on('click', '.event__delete', function() {
    /**
     * When the user removes an event, store this action in the form then hide the event.
     */
    const eventID = $(this).data('eventid');
    $('form').append('<input type="hidden" name="event-removed" value="' + eventID + '">');
    $(this).parent().hide('fast');
});

$(document).on('submit', 'form', function(event) {
    /**
     * Validate dates formats on form submit.
     */
    $('input[type="date"]').each(function() {
        const date = $(this).val();
        // If date input is empty.
        if (!date) {
            return true;
        }

        // If date is in the format DD/MM/YYYY, transform it in the ISO format YY-MM-DD.
        const isHumanDate = date.match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
        if (isHumanDate) {
            $(this).val(isHumanDate[3] + '-' + isHumanDate[2] + '-' + isHumanDate[1]);
            return true;
        }

        const isStandardDate = date.match(/^\d{4}-\d{2}-\d{2}$/);
        // If date format hasn't been recognized (neither DD/MM/YYYY nor YY-MM-DD), stop submit and show error to the user.
        if (!isStandardDate) {
            event.preventDefault();
            $(this).val('');
            $(this).parent().addClass('has-error');
            alert('Invalid date format.');
            return false;
        }
    });
});
