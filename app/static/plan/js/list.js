$(document).ready(function () {
    invokeItemList($('input[name="r_tl"]:checked'));
    $('input[name="r_tl"]').click(function () {
        invokeItemList(this)
    });
});

function invokeItemList(obj) {
    var $radio = $(obj);
    var data = {
        testlet_id: $(obj).val()
    };
    if (data.testlet_id == null) return false;

    $.ajax({
        method: 'GET',
        url: '/api/item_list/',
        data: data,
        success: function (data) {
            var str = '';
            $('#items_searched > tbody').empty();
            if (data.length == 0) {
                str = '<tr><td colspan="5">No data found.</td></tr>';
                $('#items_searched > tbody').append(str);
            } else {
                $('#items_searched > tbody').append(str);
                data.forEach(function (item) {
                    str = '<tr><td><button class="btn btn-sm btn-outline-info" type="button" name="modalButton"' +
                        ' data-toggle="modal" data-target="#dataModal" onclick=invokeModalItem(' + item[0] + ')><i class="fas fa-eye"></i></button></td>';
                    str = str + '<td class="search_item" id="item_id">' + item[0] + '</td>';
                    str = str + '<td class="search_item" id="item_name">' + item[1] + '</td>';
                    str = str + '<td class="search_item" id="item_interaction_type">' + item[2] + '</td>';
                    str = str + '<td class="search_item" id="item_level">' + item[3] + '</td></tr>';
                    $('#items_searched > tbody').append(str);
                });
            }
        }
    });
}

function invokeModalItem(id) {
    ItemRunner.init($('#dataModal .modal-content'), {mode: 'preview'});
    $('#dataModal').on('hidden.bs.modal', function (e) {
        $('#dataModal .modal-content').empty();
    });


    $('#dataModal .modal-content').html("Loading... Try again if data not shown");

    ItemRunner.getRendered(id);
}

function invokeModalTestlet(id) {
    var url = '/testlet/' + id;
    $.get(url, function (data) {
        $('#dataModal .modal-content').html(data);
    });
    $('#dataModal .modal-content').html("Loading... Try again if data not shown");
}