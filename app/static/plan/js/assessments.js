$(document).ready(function () {
    var _test_type = parent.document.getElementById("select_test_type").value;
    $('#i_test_type option').filter(function () {
        return this.value === _test_type;
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

function applyItem() {
    $('#items_searched > tbody > tr').filter(':has(:checkbox:checked)').each(function () {
        var $row = $(this);
        var $item_id = $row.find('#item_id');
        var $item_name = $row.find('#item_name');
        var $item_test_type = $row.find('#item_test_type');
        var $item_session = $row.find('#item_session_date');
        itemListFromModal($item_id.text(), $item_name.text(), $item_test_type.text(), $item_session.text());
    });
}

function itemListFromModal(id, name, test_type, session) {
    window.parent.ids += (',' + id);
    window.parent.names += (',' + name);
    window.parent.types += (',' + test_type);
    window.parent.sessions += (',' + session);
}

function searchAssessment(obj) {
    var $btn = $(obj);
    var data = {
        search_name: $('#i_name').val(),
        search_test_type: $('#i_test_type').val(),
        search_test_center: $('#i_test_center').val(),
    };
    $.ajax({
        method: 'GET',
        url: '/api/plan_assessments/',
        data: data,
        beforeSend: function () {
            $btn.attr('disabled', true);
            $('#items_searched > tbody').empty();
        },
        complete: function () {
            $btn.attr('disabled', false);
        },
        success: function (data) {
            var array_ids = window.parent.current_ids.slice(1).split(",");

            $('#items_searched > tbody').empty();
            if (data.length == 0) {
                str = '<tr><td colspan="5">No data found.</td></tr>'
                $('#items_searched > tbody').append(str);
            }
            data.forEach(function (item) {
                var flag = true;
                for (i = 0; i < array_ids.length; i++) {
                    if (array_ids[i] == item[0]) {
                        flag = false;
                        break;
                    }
                }
                if (flag) {
                    str = '<tr><td><input type="checkbox" class="item_checkbox" onclick="itemChkClick()" value="' + item[0] + '"></td>';
                    str = str + '<td class="search_item" id="item_id">' + item[0] + '</td>';
                    str = str + '<td class="search_item" id="item_name">' + item[1] + '</td>';
                    str = str + '<td class="search_item" id="item_test_type">' + item[2] + '</td>';
                    str = str + '<td class="search_item" id="item_test_center">' + item[3] + '</td>';
                    str = str + '<td class="search_item" id="item_session_date">' + item[4] + '</td></tr>';
                    $('#items_searched > tbody').append(str);
                }
            });
        }
    });
}
