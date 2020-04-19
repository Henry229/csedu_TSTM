$('button[name="modalButton"]').click(function () {
    var url = $(this).val();
    $.get(url, function (data) {
        $('#dataModal .modal-content').html(data);
    });
    $('#dataModal .modal-content').html("Loading... Try again if data not shown");
});
$('button[name="previewButton"]').click(function () {
    var item_id = $(this).data('item-id');
    ItemRunner.getRendered(item_id);
});

$('#selecctall').click(function () {
    if (this.checked) {
        $('.item_checkbox').each(function () {
            $(this).prop('checked', true);
        });
    } else {
        $('.item_checkbox').each(function () {
            $(this).prop('checked', false);
        });
    }
});

$('.item_checkbox').click(function () {
    if (!this.checked) {
        $('#selecctall').prop('checked', false);
    }
});

$('#reverse').click(function () {
    $('.item_checkbox').each(function () {
        var checked = $(this).prop('checked')
        if (checked) {
            $(this).prop('checked', false);
        } else {
            $(this).prop('checked', true);
        }
    });
});

var dropdown = {
    subject: $('#select_subject'),
    category: $('#select_category'),
    subcategory: $('#select_subcategory'),
    subject2: $('#select_subject2'),
    category2: $('#select_category2'),
    subcategory2: $('#select_subcategory2'),
    item_subject: $('.item_subjects'),
    item_category: $('.item_categories'),
    item_subcategory: $('.item_subcategories'),
    test_type: $('#select_test_type'),
    level: $('#select_level'),
    criteria: $('#select_criteria'),
};

dropdown.subject.on('change', function () {
    updateChildCode(dropdown.subject.val(), dropdown.category, 'category');
});
dropdown.category.on('change', function () {
    updateChildCode(dropdown.category.val(), dropdown.subcategory, 'subcategory');
});
dropdown.subject2.on('change', function () {
    updateChildCode(dropdown.subject2.val(), dropdown.category2, 'category');
});
dropdown.category2.on('change', function () {
    updateChildCode(dropdown.category2.val(), dropdown.subcategory2, 'subcategory');
});
dropdown.item_subject.on('change', function () {
    var $childObj = $(this).closest('tr').find("select.item_categories");
    updateChildCode(this.value, $childObj, 'category');
});
dropdown.item_category.on('change', function () {
    var $childObj = $(this).closest('tr').find("select.item_subcategories");
    updateChildCode(this.value, $childObj, 'subcategory');
});
dropdown.test_type.on('change', function () {
    updateChildCode(dropdown.test_type.val(), dropdown.level, 'level');
    updateChildCode(dropdown.test_type.val(), dropdown.criteria, 'criteria');
});

function updateChildCode(parentObjId, childObj, child_code_type) {
    var send = {
        parent: parentObjId,
        child_code_type: child_code_type
    };
    childObj.attr('disabled', 'disabled');
    childObj.empty();

    $.getJSON("/api/_get_child_codes/", send, function (data) {
        data.forEach(function (item) {
            childObj.append(
                $('<option>', {
                    value: item[0],
                    text: item[1]
                })
            );
        });
        childObj.removeAttr('disabled');
    });
}

function invokeModalTestset(id) {
    var url = '/testset/' + id;
    $.get(url, function (data) {
        $('#dataModal .modal-content').html(data);
    });
    $('#dataModal .modal-content').html("Loading... Try again if data not shown");
}

/**
 * Function renderUrlDocument(): Rendering URL HTML Document on modal window
 * @param obj : get HTML Document from url=$(obj).val
 * @param modalId : modal window object id  ex) dataModalMedium
 * @param id : id for url combination , 0 means new, null means other
 * @param parentModalId : use when this is called from Modal Window
 */
function renderUrlDocument(obj, modalId, id, parentModalId) {
    if (id == '0')
        var url = $(obj).val();
    else
        var url = $(obj).val() + '/' + _id;
    $.get(url, function (data) {
        $('#' + modalId + ' .modal-content').html(data);
    });
    if (modalId != null) {
        $('#' + parentModalId).modal("hide");
    }
    $('#' + modalId + ' .modal-content').html("Loading... Try again if data not shown");
}

/**
 * Execute Materialized View for batch data
 */
function gen_report(modal_name) {
    $.ajax({
        url: '/api/gen_report/',
        method: 'POST',
        beforeSend: function () {

        },
        complete: function () {

        },
        success: function (response) {
            console.log(response);
            $("#status").show();
            $("#status").html("Report generated successfully").fadeOut(3000, function () {
                $(this).hide()
            });
        }
    });
}

/**
 * ISO8601 - Week number of Year
 * @param dt
 * @returns {number}
 * @constructor
 */
function ISO8601_week_no(dt) {
    var tdt = new Date(dt.valueOf());
    var dayn = (dt.getDay() + 6) % 7;
    tdt.setDate(tdt.getDate() - dayn + 3);
    var firstThursday = tdt.valueOf();
    tdt.setMonth(0, 1);
    if (tdt.getDay() !== 4) {
        tdt.setMonth(0, 1 + ((4 - tdt.getDay()) + 7) % 7);
    }
    return 1 + Math.ceil((firstThursday - tdt) / 604800000);
}
