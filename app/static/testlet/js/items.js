$(document).ready(function () {
    var _grade = parent.document.getElementById("search_grade").value;
    var _subject = parent.document.getElementById("select_subject").value;
    $('#i_grade option').filter(function () {
        return this.value === _grade;
    }).prop("selected", "selected");
    $('#i_subject option').filter(function () {
        return this.value === _subject;
    }).prop("selected", "selected");
});

function selectAllClick() {
    if ($('#selectall').prop('checked')) {
        $('.item_checkbox').each(function () {
            $(this).prop('checked', true);
        });
    } else {
        $('.item_checkbox').each(function () {
            $(this).prop('checked', false);
        });
    }
}

function reverseClick() {
    $('.item_checkbox').each(function () {
        var checked = $(this).prop('checked');
        if (checked) {
            $(this).prop('checked', false);
        } else {
            $(this).prop('checked', true);
        }
    });
}

function itemChkClick() {
    if (!$('.item_checkbox').checked) {
        $('#selecctall').prop('checked', false);
    }
}

function changeCategory() {
    var dropdown = {
        i_subject: $('#i_subject'),
        i_category: $('#i_category'),
    };
    updateChildCodeItem(dropdown.i_subject, dropdown.i_category);
}

function updateChildCodeItem(parentObj, childObj) {
    var send = {
        parent: parentObj.val()
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

function applyItem() {
    $('#items_searched > tbody > tr').filter(':has(:checkbox:checked)').each(function () {
        var $row = $(this);
        var $item_id = $row.find('#item_id');
        var $item_name = $row.find('#item_name');
        var $item_category = $row.find('#item_category');
        var $item_level = $row.find('#item_level');
        itemListFromModal($item_id.text(), $item_name.text(), $item_category.text(), $item_level.text());
    });
}

function itemListFromModal(id, name, category, level) {
    window.parent.ids += (',' + id);
    window.parent.names += (',' + name);
    window.parent.types += (',' + category);
    window.parent.levels += (',' + level);
}

function searchItem() {
    var $btn = $('#item_search');
    var data = {
        search_name: $('#i_name').val(),
        search_grade: $('#i_grade').val(),
        search_subject: $('#i_subject').val(),
        search_level: $('#i_level').val(),
        search_category: $('#i_category').val(),
        search_byme: $('#i_byme').prop('checked')
    };
    $.ajax({
        method: 'GET',
        url: '/api/testlet_items/',
        data: data,
        beforeSend: function () {
            parent.is_leave = false;
            $btn.attr('disabled', true);
            var body = $('#items_searched > tbody');
            body.empty();
        },
        complete: function () {
            parent.is_leave = true;
            $btn.attr('disabled', false);
        },
        success: function (data) {
            var array_ids = window.parent.current_ids.slice(1).split(",");
            if (data.length == 0) {
                drawItemListModal();
            } else {
                data.forEach(function (item) {
                    var flag = true;
                    for (i = 0; i < array_ids.length; i++) {
                        if (array_ids[i] == item[0]) {
                            flag = false;
                            break;
                        }
                    }
                    if (flag) {
                        // item[0]:id, item[1]:name, item[2]:category, item[3]:level
                        drawItemListModal(item[0], item[1], item[2], item[3]);
                    }
                });
            }
        }
    });
}

// Draw Item List with ajax data
function drawItemListModal() {
    var body = $('#items_searched > tbody');
    modal_win = '\n<a class="btn btn-sm btn-outline-info" type="button" name="modalButtonItemInfo"' +
        ' onclick="invokeModalItemInfo(' + arguments[0] + ')" data-toggle="modal"' +
        ' data-target="#dataModalInfo"><i class="fas fa-eye"></i></a>\n';
    chk_obj = '<input type="checkbox" class="item_checkbox" value="' + arguments[0] + '">' + modal_win;
    if (arguments.length == 0) {
        tr = $('<tr><td>No Items found.</td></tr>');
    } else {
        tr = $('<tr>');
        td = $('<td>');
        chk = $(chk_obj);
        chk.val(arguments[0]);
        chk.on('click', function () {
            itemChkClick();
        });
        td.append(chk);
        tr.append(td);

        for (i = 0; i < arguments.length; i++) {
            var _id = ''
            if (i == 0) _id = 'id';
            else if (i == 1) _id = 'name';
            else if (i == 2) _id = 'category';
            else _id = 'level';

            td = $('<td id="item_' + _id + '">' + arguments[i] + '</td>');
            tr.append(td);
        }
    }
    body.append(tr);
}

// invoke from items.html - Modal box
function invokeModalItemInfo(id) {
    ItemRunner.init($('#dataModalInfo .modal-content'), {mode: 'preview'});
    $('#dataModalInfo').on('hidden.bs.modal', function (e) {
        $('#dataModalInfo .modal-content').empty();
    });

    $('#dataModalInfo .modal-content').html("Loading... Try again if data not shown");

    ItemRunner.getRendered(id);
}