var testlet_id, ids, names, levels, types, current_ids;
var g_flag = true;// set false when testsets not found
var _id;
var is_leave = false; // set true when "Save Items" button enabled

$(function () {
    $("#sortable").sortable({
        placeholder: "ui-state-highlight",
        change: function (event, ui) {
            $('#save_items').removeAttr("disabled");
            is_leave = true;
        }
    });
    $("#sortable").disableSelection();
});

window.addEventListener('beforeunload', function (e) {
    if (is_leave) {
      // Cancel the event
      e.preventDefault();
      // Chrome requires returnValue to be set
      e.returnValue = 'Are you sure to leave without save changes?';
    }
});

$(document).ready(function () {
    /**
     * Initial setup processing:
     *  Set checked attr on the first radio object
     *  Set the value to plan_id html hidden obj for Clone, Edit, Delete
     *  Rendering Testlet Detail span objects with checked testlet
     *  Disable <Save Items> button
     *  */
    $radio = $('input[name="r_tl"]');
    $radio.each(function () {
        $(this).prop('checked', true);
        return false;
    });
    $checked_radio = $('input[name="r_tl"]:checked');
    _id = $checked_radio.val();
    $('input[name="testlet_id"]').val(_id);
    invokeItemList($checked_radio);
    $('#save_items').attr("disabled", "disabled");
    /**
     * Event Handler:
     *      Radio : $('input[name="r_tl"]') click
     *      Button : <Save Items>, <Add Items>, <New>, <Edit> click
     *          - call function renderUrlDocument() from csedu_common.js
     * */
    // $('input[name="r_tl"]') Radio click
    $radio.click(function () {
        _id = $(this).val();
        $checked_radio = $(this);
        $('input[name="testlet_id"]').val(_id);
        $('#save_items').attr("disabled", "disabled");
        invokeItemList(this);
    });

    // <Save Items> button click
    $('#save_items').click(function () {
        var flag = true;
        var items = '';
        var no_items = $checked_radio.parent().siblings()[5].innerText;
        var current_no_items = $('#sortable > li > span').length;
        is_leave = false;

        if (no_items < current_no_items) {
            alert("You need to save " + no_items + " items but currently " + current_no_items + " items selected.");
            flag = false;
            is_leave = true;
            return false;
        }

        items = getListedItemIds();  // window.g_flag set data inside function
        if (window.g_flag != null)
            flag = window.g_flag;
        $('#ordered_ids').val(items);
        $('#ordered_testlet_id').val(_id);
        if (flag)
            $('#item_form').submit();
    });

    // <Add Items> button click
    $('#add_items').click(function () {
        $('#save_items').removeAttr("disabled");
        is_leave = true;
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
        levels = window.levels;

        arr_ids = ids.slice(1).split(",");
        arr_names = names.slice(1).split(",");
        arr_types = types.slice(1).split(",");
        arr_levels = levels.slice(1).split(",");

        for (i = 0; i < arr_ids.length; i++) {
            if (arr_ids[i].length != 0)
                drawItemList(arr_ids[i], arr_names[i], arr_types[i], arr_levels[i]);
        }
        drawSpanNumItems();
    });

    $("#dataModalSub").on("show.bs.modal", function () {
        window.ids = '';
        window.names = '';
        window.types = '';
        window.levels = '';
        window.current_ids = getListedItemIds('add');
    });
});

/**
 * Function getListedItemIds(): Read sortable objects and get item id list
 * @param mode: 'add' when $("#dataModalSub").on("show")
 * @returns {string}: set window.current_ids
 */
function getListedItemIds(mode) {
    var items = '';
    $('#sortable > li > span').each(function () {
        var $span = $(this);
        if (($span.text().search('No Items found.') != -1) && (mode != 'add')) {
            alert("Please add items first");
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
 * Function invokeItemList(): rendering assessment-testsets information
 * @param obj: obsolete object reference but still keep for next development
 * @returns {boolean}
 */
function invokeItemList(obj) {
    var $btn = $('#search_item');
    var data = {
        testlet_id: $(obj).val()
    };
    if (data.testlet_id == null) return false;

    $.ajax({
        method: 'GET',
        url: '/api/item_list/',
        data: data,
        beforeSend: function () {
            $btn.attr('disabled', true);
        },
        complete: function () {
            $btn.attr('disabled', false);
            drawSpanNumItems();
        },
        success: function (data) {
            var no_items = 0;
            var list = document.getElementById("sortable");

            while (list.hasChildNodes())
                list.removeChild(list.childNodes[0]);
            var i = 0;

            if (data.length == 0) {
                drawItemList();
            } else {
                data.forEach(function (item) {
                    no_items = item[4];
                    drawItemList(item[0], item[1], item[2], item[3]);
                    i++;
                });
            }
        }
    });
}

/**
 * FUnction drawSpanNumItems(): change Span Text value according to the current no_items and no_selected_items
 */
function drawSpanNumItems() {
    var no_items = $checked_radio.parent().siblings()[5].innerText;
    var no_selected_items = $('#sortable > li > span').length;
    $('#no_selected_items').text(no_selected_items + '/' + no_items);
    $('#no_selected_items').removeClass();
    if (no_items == no_selected_items)
        $('#no_selected_items').addClass("badge badge-info");
    else
        $('#no_selected_items').addClass("badge badge-danger");
}

/**
 * Function drawItemList(): called by invokeItemList() and rendering HTML objects for items
 * @param id
 * @param name
 * @param grade
 * @param subject
 */
function drawItemList(id, name, category, level) {
    var list = document.getElementById("sortable");
    var flag = false;
    // initiate when the first item including from modal box
    if (list.innerText.search('No Items found.') != -1) {
        list.removeChild(list.childNodes[0]);
    }
    var n = document.createElement("li");
    var span = document.createElement("span");
    span.className = "badge badge-light";
    span.id = 'item' + id;

    var tn='';
    if (id == null && name == null && category == null && level == null) {
        // tn = document.createTextNode('No Items found.');
        flag = true;
        return true;
    } else {
        tn = document.createTextNode(id + '  ' + name + '  ' + category + '  ' + level)
        span.appendChild(tn);
    }

    // Item deletion
    var span2 = document.createElement("a");
    span2.id = 'delete' + id;
    var i2 = document.createElement("i");
    i2.className = "cui-trash";
    span2.appendChild(i2);

    // Item Detail Modal box invoke
    var span3 = document.createElement("a");
    span3.id = 'detail' + id;
    var i3 = document.createElement("i");
    i3.className = "fas fa-eye";
    span3.appendChild(i3);

    n.appendChild(span);
    if (!flag) {   // not shown delete/info icon when item not-existing
        n.appendChild(span2);
        n.appendChild(span3);
    }
    list.appendChild(n);
    $('#delete' + id).attr("onclick", "$(this).parent().remove();$('#save_items').removeAttr('disabled');is_leave = true;drawSpanNumItems()");
    $('#detail' + id).attr("onclick", "invokeModalItem(" + id + ")");
    $('#detail' + id).attr("data-toggle", "modal");
    $('#detail' + id).attr("data-target", "#dataModal");
}

function invokeModalItem(id) {
    var url = '/item/' + id + '/preview';
    $.get(url, function (data) {
        $('#dataModal .modal-content').html(data);
    });
    $('#dataModal .modal-content').html("Loading... Try again if data not shown");
}

function invokeModalTestlet(id) {
    var url = '/testlet/' + id;
    $.get(url, function (data) {
        $('#dataModal .modal-content').html(data);
    });
    $('#dataModal .modal-content').html("Loading... Try again if data not shown");
}
