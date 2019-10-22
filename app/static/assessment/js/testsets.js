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

function applyTestset() {
    $('#testsets_searched > tbody > tr').filter(':has(:checkbox:checked)').each(function () {
        var $row = $(this);
        var $item_id = $row.find('#item_id');
        var $item_name = $row.find('#item_name');
        var $item_grade = $row.find('#item_grade');
        var $item_subject = $row.find('#item_subject');
        testsetListFromModal($item_id.text(), $item_name.text(), $item_grade.text(), $item_subject.text());
    });
}

function testsetListFromModal(id, name, grade, subject) {
    window.parent.ids += (',' + id);
    window.parent.names += (',' + name);
    window.parent.grade += (',' + grade);
    window.parent.subjects += (',' + subject);
}

function searchTestset() {
    var $btn = $('#t_search');
    var data = {
        testset_id: $('#search_id').val(),
        test_type: $('#t_type').val(),
        testset_name: $('#t_name').val(),
        grade: $('#t_grade').val(),
        subject: $('#t_subject').val()
    };
    $.ajax({
        method: 'GET',
        url: '/api/testset_list/',
        data: data,
        beforeSend: function () {
            parent.is_leave = false;
            $btn.attr('disabled', true);
            var body = $('#testsets_searched > tbody');
            body.empty();
        },
        complete: function () {
            parent.is_leave = true;
            $btn.attr('disabled', false);
        },
        success: function (data) {
            var array_ids = window.parent.current_ids.slice(1).split(",");


            if (data.length == 0) {
                drawTestsetListModal();
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
                        // item[0]:id, item[1]:name, item[2]:version, item[3]:grade, item[4]:subject
                        drawTestsetListModal(item[0], item[1], item[2], item[3], item[4]);
                    }
                });
            }
        }
    });
}

// Draw Testset List with ajax data
function drawTestsetListModal() {
    var body = $('#testsets_searched > tbody');

    modal_win = '\n<a class="btn btn-sm btn-outline-info" type="button" name="modalButtonItemInfo"' +
        ' onclick="invokeModalTestsetInfo(' + arguments[0] + ')" data-toggle="modal"' +
        ' data-target="#dataModalInfo"><i class="fas fa-eye"></i></a>\n';
    chk_obj = '<input type="checkbox" class="item_checkbox" value="' + arguments[0] + '">' + modal_win;

    if (arguments.length == 0) {
        tr = $('<tr><td>No Testsets found.</td></tr>');
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
            else if (i == 3) _id = 'grade';
            else if (i == 4) _id = 'subject';
            else _id = 'version';

            td = $('<td id="item_' + _id + '">' + arguments[i] + '</td>');
            tr.append(td);
        }
    }
    body.append(tr);
}

// invoke from items.html - Modal box
function invokeModalTestsetInfo(id) {
    var url = '/testset/' + id;
    $.get(url, function (data) {
        $('#dataModalInfo .modal-content').html(data);
        $('#dataModalInfo').modal();
    });
}
