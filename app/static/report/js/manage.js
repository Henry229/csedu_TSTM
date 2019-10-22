$(document).ready(function () {
    $("#status").hide();

    $('span[name="modalButtonSummaryReport"]').click(function () {
        var url = '/report/summary/' + $(this).attr("id") + '/' + $(this).attr("value");
        $.get(url, function (data) {
            $('#dataModalSub .modal-content').html(data);
        });
        $('#dataModalSub .modal-content').html("Loading... Try again if data not shown");
    });

    $('a[name="modalButtonTestRanking"]').click(function () {
        $btn = $(this);
        param_str = '';
        $objs = $btn.parent().siblings();
        for (i = 0; i < $objs.length; i++) {
            if (($objs[i].className=='rpt_year') || ($objs[i].className=='rpt_type') ||
                ($objs[i].className=='rpt_order') || ($objs[i].className=='rpt_id')) {
                param_str += '/' + $objs[i].id;
            }
        }
        // report/list/<string:year>/<int:test_type>/<int:sequence>/<int:assessment_id>/<int:test_center>
        var href = '/report/list' + param_str + '/' + $btn.attr("id");
        $btn.attr("href", href);
    });

    $('a[name="modalButtonTestResults"]').click(function () {
        $btn = $(this);
        param_str = '';
        $objs = $btn.parent().siblings();
        for (i = 0; i < $objs.length; i++) {

            param_str += '/' + $objs[i].id;
        }
        var href = '/report/results/pdf' + param_str;
        $btn.attr("href", href);
    });
});

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

function invokeModalItem(id) {
    var url = '/item/' + id + '/preview';
    $.get(url, function (data) {
        $('#dataModal .modal-content').html(data);
    });
    $('#dataModal .modal-content').html("Loading... Try again if data not shown");
    return false;
}