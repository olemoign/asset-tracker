'use strict';


function manageSites() {
  /**
   * Show sites corresponding to the selected tenant.
   */
  // Copy list of options (site__reference) in site__options.
  $('#site__reference').clone()
    .prop('id', 'site_id').prop('name', 'site_id')
    .appendTo('#site__options');

  const tenantIdSelected = $('#tenant_id').find('option:selected').val();

  // Filter Sites - remove irrelevant options.
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
  let siteSelect = $('#site__reference');
  siteSelect.select2('destroy');
  siteSelect.remove();
  manageSites();

  // Reselect div as it was removed/recreated.
  siteSelect = $('#site__reference');
  // Unselect the current value if we changed tenants.
  siteSelect.val('');

  siteSelect.select2({
    theme: 'bootstrap',
    width: '100%',
  });
});

function setActiveMenu(menuLinks) {
  /**
   * Activate menu tabs based on their path.
   */
  menuLinks.removeClass('active');
  const path = window.location.pathname;
  // Splitting the path name allows to highlight categories (Profiles/Oauth clients/Tenants are still highlighted
  // when creating or updating objects)
  const cat = path.split('/', 2).join('/');
  const activeLink = menuLinks.find('a[href="' + cat + '/"]');
  activeLink.parents('li').addClass('active');
}

// Manage equipments.
$(document).on('click', '.equipment__add', function addEquipment() {
  /**
   * Add a new equipment when the user clicks the '+' sign.
   */
  const equipmentBlock = $('#equipment__reference').clone();
  const nextDigit = $('.equipment__block').length;

  const equipmentSelect = equipmentBlock.find('.equipment__select');

  const newSelectId = equipmentSelect.eq(0).attr('id') + '#' + nextDigit;

  $('label[for="' + equipmentSelect.eq(0).attr('id') + '"]').attr('for', newSelectId);
  equipmentSelect.attr('id', newSelectId).attr('name', newSelectId);

  const serialNumberInput = equipmentBlock.find('.equipment__serial_number_id');
  const newSerialNumberId = serialNumberInput.eq(0).attr('id') + '#' + nextDigit;

  $('label[for="' + serialNumberInput.eq(0).attr('id') + '"]').attr('for', newSerialNumberId);
  serialNumberInput.attr('id', newSerialNumberId).attr('name', newSerialNumberId);

  equipmentBlock.removeAttr('id').removeClass('hidden').appendTo('#equipments__list');
});

$(document).on('click', '.equipment__remove', function removeEquipment() {
  /**
   * Remove an equipment when the user clicks the 'x' sign.
   */
  $(this).parents('.equipment__block').remove();
});

$(document).on('change', '.equipment__select', function addConsumableExpirationDates(event) {
  /**
   * Add expiration dates for equipments that possess consumables
   */
  const expirationDatesContainer = $(this).parents('.well');
  const equipmentBlockDigit = $(this).attr('id').split('#')[1];

  const selectedValue = event.target.value;
  const previousValue = $(this).data('prev');

  if (previousValue === selectedValue) {
    return;
  }

  $(this).data('prev', selectedValue);
  expirationDatesContainer.find('.expiration_date_fields').remove();

  const consumablesModels = $('#equipments__container').data('consumablesModels');

  if (consumablesModels[selectedValue]) {
    const equipmentsConsumablesEntries = Object.entries(consumablesModels[selectedValue]);
    equipmentsConsumablesEntries.sort((a, b) => a[1].localeCompare(b[1]));

    equipmentsConsumablesEntries.forEach(function cloneConsumableExpirationDate(element) {
      const consumableEl = $('#equipment_consumables__reference').clone().removeAttr('id').removeClass('hidden');
      const consumableId = 'equipment-expiration_date-' + element[0] + '#' + equipmentBlockDigit;

      const consumableLabel = consumableEl.find('label');
      consumableLabel.attr('for', consumableId);
      consumableLabel.text(consumableLabel.text() + element[1]);

      const consumableInput = consumableEl.find('input');
      consumableInput.attr('id', consumableId).attr('name', consumableId).val();

      expirationDatesContainer.append(consumableEl);
    });
  }
});

// Datatables.
const DATATABLES_TRANSLATIONS = {
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
      sLast: 'Dernier',
    },
    oAria: {
      sSortAscending: ': activer pour trier la colonne par ordre croissant',
      sSortDescending: ': activer pour trier la colonne par ordre d&eacute;croissant',
    },
  },
};

function addHref(row, data) {
  /**
   * Add on each row the link sent from the WebServices.
   */
  if (data.links) {
    const objectLink = $.grep(data.links, function getLink(n) {
      return n.rel === 'self';
    });
    const rowTd = $(row).find('td');

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
  const hasActiveProperty = Object.prototype.hasOwnProperty.call(data, 'is_active');
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
  const table = $('table.dataTables');
  if (!table) {
    return;
  }

  const columns = [];
  const customFilter = table.data('custom-filter');

  // Loop through all the columns, to be able to hook the 'data-render' parameters to existing functions.
  table.find('th').each(function setRenderFunctions() {
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
      url: table.data('ajax-url'),
    },
    stateSave: true,
    pageLength: 50,
    lengthChange: false,
    // Remove annoying dataTables responsive behavior when some columns are hidden.
    responsive: {
      details: false,
    },
    // Show 'processing' message.
    processing: true,
    columns: columns,
    rowCallback: assetTrackerCallback,
  };

  if (window.userLocale in DATATABLES_TRANSLATIONS) {
    dataTableParameters.language = DATATABLES_TRANSLATIONS[window.userLocale];
  }

  // If there is a custom filter, change the organization of the special divs around the dataTable (page size to
  // the bottom).
  if (customFilter) {
    dataTableParameters.dom = '<"row"<"col-sm-6"<"custom_filter checkbox">><"col-sm-6"f>>' +
      '<"row"<"col-sm-12"tr>>' +
      '<"row"<"col-sm-5"i><"col-sm-7"p>>';
  }

  const initialisedDataTable = table.DataTable(dataTableParameters);

  // Manage the custom filter.
  if (customFilter) {
    const tableContainer = $(initialisedDataTable.table().container());

    // Save the custom filter state with the other dataTables parameters.
    initialisedDataTable.on('stateSaveParams.dt', function saveCustomFilter(event, settings, data) {
      // eslint-disable-next-line no-param-reassign
      data.customFilter = !tableContainer.find('.custom_filter__input').is(':checked');
    });

    // Add the custom filter in the div created in the dom command above.
    const filterLabel = table.data('custom-filter-label');
    const tableState = initialisedDataTable.state.loaded();

    // If table didn't yet store state in local storage, input is checked, otherwise, use local storage.
    const inputIsChecked = !tableState || !tableState.customFilter ? ' checked' : '';

    const filterHTML = '<label><input class="custom_filter__input" type="checkbox"' + inputIsChecked + '> ' + filterLabel + '</label>';
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
  const api = new $.fn.dataTable.Api(settings);
  const state = api.state.loaded();

  // This is the table div.
  const table = $(event.target);

  const customFilter = table.data('custom-filter');
  if (customFilter) {
    settings.ajax.data = function setDatatablesFilter(data) {
      // This is the HTML node wrapping around the table with the special search, filter, etc.
      const dataTableContainer = $(table.DataTable().table().container());
      const customFilterInput = dataTableContainer.find('.custom_filter__input');

      // 1: the filter checkbox is visible.
      if ((customFilterInput.length && !customFilterInput.is(':checked')) ||
        // 2: the table isn't visible yet but a filter value is present in the local storage.
        (!customFilterInput.length && state && state.customFilter)) {
        // noinspection JSUndefinedPropertyAssignment
        data.filter = customFilter;
      }
    };
  }
});

$(document).on('click', '.event__delete', function removeEvent() {
  /**
   * When the user removes an event, store this action in the form then hide the event.
   */
  const eventID = $(this).data('eventid');
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
    const humanPattern = /^(\d{2})\/(\d{2})\/(\d{4})$/;
    if (humanPattern.test(this.value)) {
      this.value = this.value.replace(humanPattern, '$3-$2-$1');
      this.setCustomValidity('');
      return;
    }

    // Date is in the expected format YYYY-MM-DD.
    const isoPattern = /^\d{4}-\d{2}-\d{2}$/;
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
      if (!this.value) {
        return;
      }

      // If date is in the format YYYY-MM-DD, transform it in the format DD/MM/YYYY.
      const isStandardDate = this.value.match(/^(\d{4})-(\d{2})-(\d{2})$/);
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
  const firstInput = $('input[type=text]').first();
  firstInput.trigger('focus');
  // Move cursor to the end of the input.
  firstInput.val(firstInput.val());

  restoreDates();

  // Show sites corresponding to the selected tenant when page is ready.
  manageSites();

  // select2 overrides standard select
  $('select').select2({
    theme: 'bootstrap',
    width: '100%',
  });
});
