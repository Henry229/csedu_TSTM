$(document).ready(function () {
    invokeTestsetList($('input[name="r_tl"]:checked'));
    $('input[name="r_tl"]').click(function () {
        invokeTestsetList(this)
    });
});

function invokeTestsetList(obj) {
    var $radio = $(obj);
    var $btn = $('#search_item');
    var data = {
        id: $(obj).val()
    };
    $.ajax({
        method: 'GET',
        url: '/api/testsets/',
        data: data,
        beforeSend: function () {
            $btn.attr('disabled', true);
        },
        success: function (data) {
            var str = '';
            $('#testsets_searched > tbody').empty();
            if (data.length == 0) {
                str = '<tr><td colspan="5">No data found.</td></tr>';
                $('#testsets_searched > tbody').append(str);
            } else {
                $('#testsets_searched > tbody').append(str);
                data.forEach(function (item) {
                    str = '<tr><td><button class="btn btn-sm btn-outline-info" type="button" name="modalButton"' +
                        ' data-toggle="modal" data-target="#dataModal" onclick=invokeModalTestset(' + item[0] + ')><i class="fas fa-eye"></i></button>' +
                        ' <button class="btn btn-sm btn-outline-info" type="button" style="padding-left:10px;padding-right:10px" onclick=makeTestQeustions(this,' + item[0] + ')><i class="fas fa-plus"></i></button>';
                    str = str + '</td>';
                    str = str + '<td class="search_item" id="item_id">' + item[0] + '</td>';
                    str = str + '<td class="search_item" id="item_name">' + item[1] + '</td>';
                    str = str + '<td class="search_item" id="item_grade">' + item[2] + '</td>';
                    str = str + '<td class="search_item" id="item_subject">' + item[3] + '</td></tr>';
                    $('#testsets_searched > tbody').append(str);
                });
            }
        }
    });
}

function invokeModalTestset(id) {
    var url = '/testset/' + id;
    $.get(url, function (data) {
        $('#dataModal .modal-content').html(data);
        $('#dataModal').modal();
    });
}

function makeTestQeustions(o, id){
    if(!confirm("Would you like to set the questions into Items?")) return;

    var $btn = $(o);
    var data = {
        id: id
    };
    $.ajax({
        method: 'GET',
        url: '/api/testsets/questions/',
        data: data,
        beforeSend: function () {
            $btn.attr('disabled', true);
        },
        success: function (data) {
            alert('The questions are generated')
        },
        error: function (xhr) {
            alert('A system error occurred');
        },
        complete : function () {
            $btn.attr('disabled', false);
        }
    });

}