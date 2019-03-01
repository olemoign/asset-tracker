'use strict';

var GLUCOMETER_FAMILY_ID = '2YUEMLmH';


function manageSites() {
    /**
     * Show sites corresponding to the selected tenant.
     */
    // Copy list of options (site__reference) in site__options
    $('#site__reference').clone()
        .prop('id', 'site_id').prop('name', 'site_id')
        .addClass('custom_select2')
        .show()
        .appendTo('#site__options');

    var tenantIdSelected = $('#tenant_id').find('option:selected').val();

    // Filter Sites - remove irrelevant options
    $('#site_id').children('option').each(function removeSitesFromOtherTenants() {
        if ($(this).data('tenant_id') && $(this).data('tenant_id') !== tenantIdSelected) {
            $(this).remove();
        }
    });
}

$(document).on('change', '#tenant_id', function manageSiteSelect() {
    /**
     * Manage the site dropdown when a new tenant is selected.
     * select2 doesn't understand the 'hide' attribute - select is rebuilt every time a new tenant is selected.
     */
    var siteSelect = $('.custom_select2');
    siteSelect.select2('destroy');
    siteSelect.remove();
    manageSites();

    // Reselect div as it was removed/recreated.
    siteSelect = $('.custom_select2');
    // Unselect the current value if we changed tenants.
    siteSelect.val('');

    siteSelect.select2({
        theme: 'bootstrap',
        width: '100%'
    });
});

function setActiveMenu(menuLinks) {
    /**
     * Activate menu tabs based on their path.
     */
    menuLinks.removeClass('active');
    var path = window.location.pathname;
    // Splitting the path name allows to highlight categories (Profiles/Oauth clients/Tenants are still highlighted
    // when creating or updating objects)
    var cat = path.split('/', 2).join('/');
    var activeLink = menuLinks.find('a[href="' + cat + '/"]');
    activeLink.parents('li').addClass('active');
}

// Manage equipments.
$(document).on('click', '.equipment__add', function addEquipment() {
    /**
     * Add a new equipment when the user clicks the '+' sign.
     */
    $('#equipment__reference').clone().removeAttr('id').show()
        .appendTo('#equipments__list');
});

$(document).on('click', '.equipment__remove', function removeEquipment() {
    /**
     * Remove an equipment when the user clicks the 'x' sign.
     */
    $(this).parents('.equipment__block').remove();
});

$(document).on('change', '.equipment__select', function addGlucometerExpirations() {
    /**
     * Add expiration dates for Glucometer equipment
     */
    var expirationDateFields = $(this).parents('.equipment__block').find('.expiration_date_fields');

    if ($(this).val() === GLUCOMETER_FAMILY_ID) {
        expirationDateFields.show();
    } else {
        expirationDateFields.hide();
        expirationDateFields.find('input').val('');
    }
});

// Datatables.
var dataTablesTranslations = {
    fr: {
        sProcessing: 'Traitement en cours...',
        sSearch: 'Rechercher&nbsp;:',
        sLengthMenu: 'Afficher _MENU_ &eacute;l&eacute;ments',
        sInfo: 'Affichage de l\'&eacute;l&eacute;ment _START_ &agrave; _END_ sur _TOTAL_ &eacute;l&eacute;ments',
        sInfoEmpty: 'Affichage de l\'&eacute;l&eacute;ment 0 &agrave; 0 sur 0 &eacute;l&eacute;ments',
        sInfoFiltered: '(filtr&eacute; de _MAX_ &eacute;l&eacute;ments au total)',
        sInfoPostFix: '',
        sLoadingRecords: 'Chargement en cours...',
        sZeroRecords: 'Aucun &eacute;l&eacute;ment &agrave; afficher',
        sEmptyTable: 'Aucune donn&eacute;e disponible dans le tableau',
        oPaginate: {
            sFirst: 'Premier',
            sPrevious: 'Pr&eacute;c&eacute;dent',
            sNext: 'Suivant',
            sLast: 'Dernier'
        },
        oAria: {
            sSortAscending: ': activer pour trier la colonne par ordre croissant',
            sSortDescending: ': activer pour trier la colonne par ordre d&eacute;croissant'
        }
    }
};

function addHref(row, data) {
    /**
     * Add on each row the link sent from the WebServices.
     */
    if (data.links) {
        var objectLink = $.grep(data.links, function getLink(n) {
            return n.rel === 'self';
        });
        var rowTd = $(row).find('td');

        rowTd.each(function fillCell() {
            // If cell is empty, add a space character so that the cell will be clickable.
            if (!$(this).html()) {
                $(this).html('&nbsp;');
            }
            $(this).wrapInner('<a href="' + objectLink[0].href + '"></a>');
        });
    }
}

function styleInactiveObjects(row, data) {
    var hasActiveProperty = Object.prototype.hasOwnProperty.call(data, 'is_active');
    // noinspection JSUnresolvedVariable
    if (hasActiveProperty && !data.is_active) {
        $(row).addClass('warning');
    }
}

function assetTrackerCallback(row, data) {
    addHref(row, data);
    styleInactiveObjects(row, data);
}

function createDataTables() {
    /**
     * Create the dataTable.
     */
    var table = $('table.dataTables');
    if (!table) {
        return;
    }

    var columns = [];
    var customFilter = table.data('custom-filter');

    // Loop through all the columns, to be able to hook the 'data-render' parameters to existing functions.
    table.find('th').each(function setRenderFunctions() {
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
        // Remove annoying dataTables responsive behavior when some columns are hidden.
        responsive: {
            details: false
        },
        // Show 'processing' message.
        processing: true,
        columns: columns,
        columnDefs: [{
            targets: '_all',
            render: $.fn.dataTable.render.text()
        }],
        rowCallback: assetTrackerCallback
    };

    if (userLocale !== 'en') {
        dataTableParameters.language = dataTablesTranslations[userLocale];
    }

    // If there is a custom filter, change the organization of the special divs around the dataTable (page size to
    // the bottom).
    if (customFilter) {
        dataTableParameters.dom = '<"row"<"col-sm-6"<"custom_filter checkbox">><"col-sm-6"f>>'
                                + '<"row"<"col-sm-12"tr>>'
                                + '<"row"<"col-sm-5"i><"col-sm-7"p>>';
    }

    var initialisedDataTable = table.DataTable(dataTableParameters);

    // Manage the custom filter.
    if (customFilter) {
        var tableContainer = $(initialisedDataTable.table().container());

        // Save the custom filter state with the other dataTables parameters.
        initialisedDataTable.on('stateSaveParams.dt', function saveCustomFilter(event, settings, data) {
            // eslint-disable-next-line no-param-reassign
            data.customFilter = !tableContainer.find('.custom_filter__input').is(':checked');
        });

        // Add the custom filter in the div created in the dom command above.
        var filterLabel = table.data('custom-filter-label');
        var tableState = initialisedDataTable.state.loaded();

        var filterInit = table.data('custom-filter-default') === true;
        // If table didn't yet store state in local storage, take default value, otherwise, use local storage.
        var inputIsChecked = (!tableState && !filterInit) || (tableState && !tableState.customFilter) ? ' checked' : '';

        var filterHTML = '<label><input class="custom_filter__input" type="checkbox"' + inputIsChecked + '> ' + filterLabel + '</label>';
        tableContainer.find('.custom_filter').html(filterHTML);
        initialisedDataTable.state.save();

        // Force a draw of the table when the filter state changes.
        tableContainer.find('.custom_filter__input').on('change', initialisedDataTable.draw);
    }

    // If an ajax call is long, the user can browse before the response is received. As the state is by default
    // saved after reception of the reponse, the state changes can be lost.
    // To prevent this, save the state before making the ajax request.
    table.on('preXhr.dt', initialisedDataTable.state.save);
}

$(document).on('preInit.dt', function initCustomFilter(event, settings) {
    /**
     * Before dataTable initialization, manage when to send the 'hide' query string for the custon filter.
     */
    /* eslint-disable no-param-reassign */
    var api = new $.fn.dataTable.Api(settings);
    var state = api.state.loaded();

    // This is the table div.
    var table = $(event.target);

    var customFilter = table.data('custom-filter');
    if (customFilter) {
        settings.ajax.data = function setDatatablesFilter(data) {
            // This is the HTML node wrapping around the table with the special search, filter, etc.
            var dataTableContainer = $(table.DataTable().table().container());
            var customFilterInput = dataTableContainer.find('.custom_filter__input');
            var filterInit = table.data('custom-filter-default') === true;

            // 1: the filter checkbox is visible.
            if ((customFilterInput.length && !customFilterInput.is(':checked'))
            // 2: the table isn't visible yet but a filter value is present in the local storage.
            || (!customFilterInput.length && state && state.customFilter)
            // 3: this is the first time we load the table, use the default value.
            || (!customFilterInput.length && !state && filterInit)) {
                // noinspection JSUndefinedPropertyAssignment
                data.filter = customFilter;
            }
        };
    }
});

$(document).on('click', '.paginate_button', function animateTablePaginate() {
    /**
     * Scroll to top of dataTable when changing page.
     */
    $('body').animate({ scrollTop: 0 }, 'slow');
});

$(document).on('click', '.event__delete', function removeEvent() {
    /**
     * When the user removes an event, store this action in the form then hide the event.
     */
    var eventID = $(this).data('eventid');
    $('form').append('<input type="hidden" name="event-removed" value="' + eventID + '">');
    $(this).parent().hide('fast');
});

$(document).on('submit', 'form', function validateDates(event) {
    /**
     * Validate dates on form submit.
     */
    $(this).find('input[type="date"]').each(function validateDate() {
        // Date is null.
        if (!this.value) {
            this.setCustomValidity('');
            return;
        }

        // Date is in the format DD/MM/YYYY, transform it in the ISO format YYYY-MM-DD.
        var humanPattern = /^(\d{2})\/(\d{2})\/(\d{4})$/;
        if (humanPattern.test(this.value)) {
            this.value = this.value.replace(humanPattern, '$3-$2-$1');
            this.setCustomValidity('');
            return;
        }

        // Date is in the expected format YYYY-MM-DD.
        var isoPattern = /^\d{4}-\d{2}-\d{2}$/;
        if (isoPattern.test(this.value)) {
            this.setCustomValidity('');
            return;
        }

        // Date format hasn't been recognized, show error to the user and stop submit.
        this.setCustomValidity('Invalid date.');
    });

    if (!this.reportValidity()) {
        event.preventDefault();
    }
});

$(document).on('input', 'input[type="date"]', function resetCustomValidity() {
    // Reset customValidity on input change, otherwise Safari will not fire form submit.
    this.setCustomValidity('');
});

function restoreDates() {
    // Update date format if browser doesn't manage date input types.
    if (!Modernizr.inputtypes.date) {
        $('input[type="date"]').each(function standardizeDates() {
            // If date is null.
            if (!this.value) return;

            // If date is in the format YYYY-MM-DD, transform it in the format DD/MM/YYYY.
            var isStandardDate = this.value.match(/^(\d{4})-(\d{2})-(\d{2})$/);
            if (isStandardDate) {
                this.value = isStandardDate[3] + '/' + isStandardDate[2] + '/' + isStandardDate[1];
            }
        });
    }
}

$(function preparePageReady() {
    setActiveMenu($('#menu-main li, #menu-settings li'));

    createDataTables();

    // Auto focus first input in page.
    var firstInput = $('input[type=text]').first();
    firstInput.trigger('focus');
    // Move cursor to the end of the input.
    firstInput.val(firstInput.val());

    restoreDates();

    // Show sites corresponding to the selected tenant when page is ready.
    manageSites();

    // select2 overrides standard select
    $('.custom_select2').select2({
        theme: 'bootstrap',
        width: '100%'
    });
});
