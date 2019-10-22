var plan_id, ids, names, sessions, types, current_ids;
var g_flag = true; // set false when assessments not found
var _id;

$(function () {
    $("#sortable").sortable({
        placeholder: "ui-state-highlight"
    });
    $("#sortable").disableSelection();
});

$(document).ready(function () {
    /**
     * Initial setup processing:
     *  Set checked attr on the first radio object
     *  Set the value to plan_id html hidden obj for Clone, Edit, Delete
     *  Rendering Education Plan Detail span objects with checked plan
     *  Disable <Save Assessments> button
     *  */
    $radio = $('input[name="r_tl"]');
    $radio.each(function () {
        $(this).prop('checked', true);
        return false;
    });
    $checked_radio = $('input[name="r_tl"]:checked');
    _id = $checked_radio.val();
    $('input[name="plan_id"]').val(_id);
    invokePlanDetailList($checked_radio);
    $('#save_assessments').attr("disabled", "disabled");

    /**
     * Event Handler:
     *      Radio : $('input[name="r_tl"]') click
     *      Button : <Save Assessments>, <Add Assessments>, <New>, <Edit> click
     *          - call function renderUrlDocument() from csedu_common.js
     * */
    // $('input[name="r_tl"]') Radio click
    $radio.click(function () {
        _id = $(this).val();
        $checked_radio = $(this);
        $('input[name="plan_id"]').val(_id);
        $('#save_assessments').attr("disabled", "disabled");
        invokePlanDetailList(this);
    });

    // <Save Assessments> button click
    $('#save_assessments').click(function () {
        var flag = true;
        var items = getListedItemIds();
        if (window.g_flag != null)
            flag = window.g_flag;
        $('#ordered_ids').val(items);
        $('#ordered_plan_id').val($('input[name="r_tl"]:checked').val());
        if (flag)
            $('#item_form').submit();
    });

    // <Add Assessments> button click
    $('#add_assessments').click(function () {
        $('#save_assessments').removeAttr("disabled");
        renderUrlDocument(this, 'dataModalSub');
    });

    // <New> button click
    $('button[name="modalButtonNew"]').click(function () {
        renderUrlDocument(this, 'dataModalMedium', 0); //set id 0 for new
    });

    // <Edit> button click
    $('button[name="modalButtonEdit"]').click(function () {
        renderUrlDocument(this, 'dataModalMedium');
    });

    /**
     * Modal dataModalSub: rendering search details page
     * Set relevant data to share between parent and modal windows
     */
    $("#dataModalSub").on("hidden.bs.modal", function () {
        ids = window.ids;
        names = window.names;
        types = window.types;
        sessions = window.sessions;

        arr_ids = ids.slice(1).split(",");
        arr_names = names.slice(1).split(",");
        arr_types = types.slice(1).split(",");
        arr_sessions = sessions.slice(1).split(",");

        for (i = 0; i < arr_ids.length; i++) {
            if (arr_ids[i].length != 0)
                drawItemList(arr_ids[i], arr_names[i], arr_types[i], arr_sessions[i]);
        }
    });

    $("#dataModalSub").on("show.bs.modal", function () {
        window.ids = '';
        window.names = '';
        window.types = '';
        window.sessions = '';
        window.current_ids = getListedItemIds('add');
    });
});

/**
 * Function getListedItemIds(): Read sortable objects and get assessment id list
 * @param mode: 'add' when $("#dataModalSub").on("show")
 * @returns {string}: set window.current_ids
 */
function getListedItemIds(mode) {
    var items = '';
    $('#sortable > li > span').each(function () {
        var $span = $(this);
        if (($span.text().search('No Assessments found.') != -1) && (mode != 'add')) {
            alert("Please add Assessments first");
            window.g_flag = false;
        } else {
            var item = $span.text().split(" ");
            items = items + ',' + item[0];
            window.g_flag = true;
        }
    });
    return items;
}

/**
 * Function invokePlanDetailList(): rendering education plan - assessments information
 * @param obj: obsolete object reference but still keep for next development
 * @returns {boolean}
 */
function invokePlanDetailList(obj) {
    var $btn = $('#search_item');
    var data = {
        plan_id: _id
    };
    if (data.plan_id == null) return false;

    $.ajax({
        method: 'GET',
        url: '/api/assessment_list/',
        data: data,
        beforeSend: function () {
            $btn.attr('disabled', true);
        },
        success: function (data) {
            var list = document.getElementById("sortable");

            while (list.hasChildNodes())
                list.removeChild(list.childNodes[0]);
            var i = 0;

            if (data.length == 0) {
                drawItemList();
            } else {
                data.forEach(function (item) {
                    // item[0]: id, item[1]: name, item[2]: test_type, item[3]: test_center, item[4]: year
                    drawItemList(item[0], item[1], item[2], item[4]);
                    i++;
                });
            }
        }
    });
}

/**
 * Function drawItemList(): called by invokePlanDetailList() and rendering HTML objects for assessments
 * @param id
 * @param name
 * @param test_type
 * @param session_date
 */
function drawItemList(id, name, test_type, session_date) {
    var list = document.getElementById("sortable");
    var flag = false;
    // initiate when the first item including from modal box
    if (list.innerText.search('No Assessments found.') != -1) {
        list.removeChild(list.childNodes[0]);
    }
    var n = document.createElement("li");
    var span = document.createElement("span");
    span.className = "badge badge-light";

    var tn;
    if (id == null && name == null && test_type == null && session_date == null) {
        // tn = document.createTextNode('No Assessments found.');
        flag = true;
        return true;
    } else {
        tn = document.createTextNode(id + '  ' + name + '  ' + test_type + '  ' + session_date)
        span.appendChild(tn);
    }

    // Item deletion
    var span2 = document.createElement("a");
    span2.id = 'delete' + id;
    var i2 = document.createElement("i");
    i2.className = "cui-trash";
    span2.appendChild(i2);
    n.appendChild(span);
    if (!flag) {   // not shown delete/info icon when item not-existing
        n.appendChild(span2);
    }
    list.appendChild(n);
    $('#delete' + id).attr("onclick", "$(this).parent().remove();$('#save_assessments').removeAttr('disabled');");
}
