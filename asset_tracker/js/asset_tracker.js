/* global $ */

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
    if ($(this).data('tenant-id') && $(this).data('tenant-id') !== tenantIdSelected) {
      $(this).remove();
    }
  });
}

$(document).on('change', '#tenant_id', function manageSiteSelect() {
  /**
   * Manage the site dropdown when a new tenant is selected.
   * select2 doesn't understand the 'hide' attribute - select is rebuilt every time a new tenant is selected.
   */
  let siteSelect = $('#site_id');
  siteSelect.select2('destroy');
  siteSelect.remove();
  manageSites();

  // Reselect div as it was removed/recreated.
  // noinspection JSJQueryEfficiency
  siteSelect = $('#site_id');
  // Unselect the current value if we changed tenants.
  siteSelect.val('');

  siteSelect.select2({
    theme: 'bootstrap',
    width: '100%',
  });
});

function manageCalibrationFrequency() {
  const assetType = $('#asset_type');
  const calibrationFrequency = $('#calibration_frequency').parent();
  if (assetType.val() === 'consumables_case') {
    calibrationFrequency.addClass('hidden');
  } else {
    calibrationFrequency.removeClass('hidden');
  }
}
$(document).on('change', '#asset_type', manageCalibrationFrequency);

function setActiveMenu(menuLinks) {
  /**
   * Activate menu tabs based on their path.
   */
  menuLinks.removeClass('active');
  const path = window.location.pathname;
  // Splitting the path name allows to highlight categories (Profiles/Oauth clients/Tenants are still highlighted
  // when creating or updating objects)
  const cat = path.split('/', 2).join('/');
  const activeLink = menuLinks.find(`a[href="${cat}/"]`);
  activeLink.parent('li').addClass('active');
}

// Manage equipments.
$(document).on('click', '.equipment__add', function addEquipment(event) {
  /**
   * Add a new equipment when the user clicks the '+' sign.
   */
  event.stopPropagation();

  const panel = $(this).closest('.panel.panel-default');
  panel.removeClass('no-equipment');
  panel.find('.collapse').collapse('show');

  const equipmentBlock = $('#equipments__reference').clone();

  let equipmentsCounter = 0;
  // Get the current biggest counter value.
  $('.equipment__block').each(function getCounter() {
    if ($(this).data('equipments-counter') > equipmentsCounter) {
      equipmentsCounter = $(this).data('equipments-counter');
    }
  });
  equipmentsCounter += 1;

  const equipmentSelect = equipmentBlock.find('.equipment__family');
  const modelSelectId = equipmentSelect.eq(0).attr('id');
  const newSelectId = `${equipmentsCounter}#${modelSelectId}`;
  $(`label[for="${modelSelectId}"]`).attr('for', newSelectId);
  equipmentSelect.attr('id', newSelectId).attr('name', newSelectId);

  const serialNumberInput = equipmentBlock.find('.equipment__serial_number');
  const modelSerialNumberId = serialNumberInput.eq(0).attr('id');
  const newSerialNumberId = `${equipmentsCounter}#${modelSerialNumberId}`;
  $(`label[for="${modelSerialNumberId}"]`).attr('for', newSerialNumberId);
  serialNumberInput.attr('id', newSerialNumberId).attr('name', newSerialNumberId);

  equipmentBlock.attr('data-equipments-counter', equipmentsCounter)
    .removeAttr('id').removeClass('hidden')
    .appendTo('#equipments__list');
  equipmentBlock.find('select').select2({
    theme: 'bootstrap',
    width: '100%',
  });
});

$(document).on('click', '.equipment__remove', function removeEquipment() {
  /**
   * Remove an equipment when the user clicks the 'x' sign.
   */
  // No equipment, only reference remains.
  // We need to do this check before removing, otherwise the $(this) node doesn't exist anymore and $(this).closest()
  // returns empty.
  if ($('.equipment__block').length === 2) {
    console.log($(this).closest('.panel.panel-default'));
    $(this).closest('.panel.panel-default').addClass('no-equipment');
  }

  $(this).closest('.equipment__block').remove();
});

$(document).on('change', '.equipment__family', function addConsumableExpirationDates(event) {
  /**
   * Add expiration dates for equipments that possess consumables.
   */
  const equipmentContainer = $(this).closest('.equipment__block');
  const expirationDates = equipmentContainer.find('.expiration_dates');
  const equipmentCounter = equipmentContainer.data('equipments-counter');

  const selectedValue = event.target.value;
  expirationDates.empty();

  const consumablesFamilies = $('#equipments__container').data('consumables-families');

  if (consumablesFamilies[selectedValue]) {
    const equipmentsConsumablesEntries = Object.entries(consumablesFamilies[selectedValue]);
    equipmentsConsumablesEntries.sort((a, b) => a[1].localeCompare(b[1]));

    equipmentsConsumablesEntries.forEach(function cloneConsumableExpirationDate(element) {
      const consumableEl = $('#equipments_consumables__reference').clone().removeAttr('id').removeClass('hidden');
      const consumableId = `${equipmentCounter}#${element[0]}-expiration_date`;

      const consumableLabel = consumableEl.find('label');
      consumableLabel.attr('for', consumableId);
      consumableLabel.text(element[1]);

      const consumableInput = consumableEl.find('input');
      consumableInput.attr('id', consumableId).attr('name', consumableId);

      expirationDates.append(consumableEl);
    });
  }
});

/** * DATATABLES ** */
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
      sSeparator: 'sur',
    },
    oAria: {
      sSortAscending: ': activer pour trier la colonne par ordre croissant',
      sSortDescending: ': activer pour trier la colonne par ordre d&eacute;croissant',
    },
  },
};


function addHrefToDataTablesRows(row, data) {
  /**
   * Add on each row the link sent from the WebServices.
   */
  if (data.links) {
    const objectLink = jQuery.grep(data.links, function getLink(n) {
      return n.rel === 'self';
    });

    const rowTd = $(row).find('td');
    rowTd.each(function fillCell() {
      // If cell is empty, add a space character so that the cell will be clickable.
      if (!$(this).html()) {
        $(this).html('&nbsp;');
      }
      $(this).wrapInner(`<a href="${objectLink[0].href}"></a>`);
    });
  }
}

function cancelColReorderEvents() {
  $(document).unbind('touchmove.ColReorder');
  $(document).unbind('mousemove.ColReorder');
  $(document).unbind('mouseup.ColReorder');
  $(document).unbind('touchend.ColReorder');
}

function manageColumnsRender(table) {
  const columns = [];

  // Loop through all the columns, to be able to hook the 'data-render' parameters to existing functions.
  table.find('th').each(function setRenderFunctions() {
    const col = {};
    // We can't set the render functions using HTML5 data parameters, so we simulate this behavior.
    const renderFunction = $(this).data('render');
    if (renderFunction) {
      col.render = window[renderFunction];
    }
    columns.push(col);
  });

  return columns;
}

function styleInactiveObjects(row, data) {
  const hasActiveProperty = Object.prototype.hasOwnProperty.call(data, 'is_active');
  // noinspection JSUnresolvedVariable
  if (hasActiveProperty && !data.is_active) {
    $(row).addClass('warning');
  }
}

function assetTrackerCallback(row, data) {
  addHrefToDataTablesRows(row, data);
  styleInactiveObjects(row, data);
}

$(function createDatatables() {
  /**
   * Create the dataTable.
   */
  const table = $('table.dataTables');
  if (!table) {
    return;
  }

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
    columns: manageColumnsRender(table),
    rowCallback: assetTrackerCallback,
    colReorder: true,
    colResize: {
      isEnabled: true,
      isResizable: function(column) {
        return !!column.sTitle;
      },
      onResizeStart: cancelColReorderEvents,
      onResize: cancelColReorderEvents,
    },
  };

  if (window.userLocale in DATATABLES_TRANSLATIONS) {
    dataTableParameters.language = DATATABLES_TRANSLATIONS[window.userLocale];
  }

  const customFilter = table.data('custom-filter');
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
    tableContainer.find('.dataTables_info').css('padding-bottom', '10px');

    // Save the custom filter state with the other dataTables parameters.
    initialisedDataTable.on('stateSaveParams.dt', function saveCustomFilter(event, settings, data) {
      data.customFilter = !tableContainer.find('.custom_filter__input').is(':checked');
    });

    // Add the custom filter in the div created in the dom command above.
    const filterLabel = table.data('custom-filter-label');
    const tableState = initialisedDataTable.state.loaded();

    // If table didn't yet store state in local storage, input is checked, otherwise, use local storage.
    const inputIsChecked = !tableState || !tableState.customFilter ? ' checked' : '';
    const filterHTML = `<label><input class="custom_filter__input" type="checkbox"${inputIsChecked}> ${filterLabel}</label>`;
    tableContainer.find('.custom_filter').html(filterHTML).css('padding', '10px 0 0 10px');
    initialisedDataTable.state.save();

    // Force a draw of the table when the filter state changes.
    tableContainer.find('.custom_filter__input').on('change', initialisedDataTable.draw);
  }

  // If an ajax call is long, the user can browse before the response is received. As the state is by default
  // saved after reception of the reponse, the state changes can be lost.
  // To prevent this, save the state before making the ajax request.
  table.on('preXhr.dt', initialisedDataTable.state.save);
});

$(document).on('preInit.dt', function initCustomFilter(event, settings) {
  /**
   * Before dataTable initialization, manage when to send the 'hide' query string for the custon filter.
   */
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
        data.filter = customFilter;
      }
    };
  }
});

$(document).on('click', '.event__delete', function removeEvent() {
  /**
   * When the user removes an event, store this action in the form then hide the event.
   */
  const eventID = $(this).data('event-id');
  $('form').append(`<input type="hidden" name="event-removed" value="${eventID}">`);
  $(this).parent().hide('fast');
});

$(document).on('click', '.panel_link', function followRTALink(event) {
  /**
   * Follow RTA link, prevent being overriden by panel collapse.
   */
  event.stopPropagation();
  window.location = $(this).prop('href');
});

$(function preparePageReady() {
  setActiveMenu($('#menu-main li, #menu-settings li'));

  // Autofocus first input in page.
  const firstInput = $('input[type=text]').first();
  firstInput.trigger('focus');
  // Move cursor to the end of the input.
  firstInput.val(firstInput.val());

  // Show or hide calibration frequency depending on asset type.
  manageCalibrationFrequency();
  // Show sites corresponding to the selected tenant when page is ready.
  manageSites();

  // Activate Select2.
  $('select:visible').select2({
    theme: 'bootstrap',
    width: '100%',
  });
});
