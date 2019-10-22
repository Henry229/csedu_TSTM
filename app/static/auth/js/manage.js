$(document).ready(function () {
    $radio = $('input[name="r_tl"]');
    $radio.each(function () {
        $(this).prop('checked', true);
        return false;
    });

    $('button[name="modalButtonNew"]').click(function () {
        var url = $(this).val();
        $.get(url, function (data) {
            $('#dataModalMedium .modal-content').html(data);
        });
        $('#dataModalMedium .modal-content').html("Loading... Try again if data not shown");
    });

    $('button[name="modalButtonEdit"]').click(function () {
        var id = $('input[name="r_tl"]:checked').val();
        var url = $(this).val() + '/' + id;
        $.get(url, function (data) {
            $('#dataModalMedium .modal-content').html(data);
        });
        $('#dataModalMedium .modal-content').html("Loading... Try again if data not shown");
    });

    $('a[name="modalButtonPassword"]').click(function () {
        var url = $(this).attr("href");
        $.get(url, function (data) {
            $('#dataModalMedium .modal-content').html(data);
        });
        $('#dataModalMedium .modal-content').html("Loading... Try again if data not shown");
    });

    $('button[name="modalButtonDelete"]').click(function () {
        var id = $('input[name="r_tl"]:checked').val();
        $('input[name="user_id"]').val(id);
    });
});