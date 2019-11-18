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
        // report/test_ranking/<string:year>/<int:test_type>/<int:sequence>/<int:assessment_id>/<int:test_center>
        var href = '/report/test_ranking' + param_str + '/' + $btn.attr("id");
        $btn.attr("href", href);
    });

    $('a[name="btnTestReports"]').click(function () {
        $btn = $(this);
        param_str = '';
        $objs = $btn.parent().siblings();
       for (i = 0; i < $objs.length; i++) {
            if (($objs[i].className=='rpt_year') || ($objs[i].className=='rpt_type') ||
                ($objs[i].className=='rpt_order') || ($objs[i].className=='rpt_id')) {
                param_str += '/' + $objs[i].id;
            }
        }
        // report/test_ranking/<string:year>/<int:test_type>/<int:sequence>/<int:assessment_id>/<int:test_center>
        var href = '/report/results/pdf' + param_str + '/' + $btn.attr("id");
        $btn.attr("href", href);
    });

    $('a[name="btnTestAssessmentReports"]').click(function () {
        $btn = $(this);
        param_str = '';
        $objs = $btn.parent().siblings();
       for (i = 0; i < $objs.length; i++) {
            if (($objs[i].className=='rpt_year') || ($objs[i].className=='rpt_type') ||
                ($objs[i].className=='rpt_order') || ($objs[i].className=='rpt_id')) {
                param_str += '/' + $objs[i].id;
            }
        }
        // report/test_ranking/<string:year>/<int:test_type>/<int:sequence>/<int:assessment_id>/<int:test_center>
        var href = '/report/results/pdf' + param_str + '/' + $btn.attr("id");
        $btn.attr("href", href);
    });

});

function getTestReport(assessment_id, testset_id) {
    var url = '/report/ts/'+assessment_id+'/'+testset_id+'/'+$("#select_student option:selected").val();
    $('a[name="btnTestReport"]').attr("href",url);
}

function getAssessmentReport(assessment_id) {
    var url = '/report/student/set/'+assessment_id+'/'+$("#select_student option:selected").val();
    $('a[name="btnTestReport"]').attr("href",url);
}


function invokeModalItem(id) {
    var url = '/item/' + id + '/preview';
    $.get(url, function (data) {
        $('#dataModal .modal-content').html(data);
    });
    $('#dataModal .modal-content').html("Loading... Try again if data not shown");
    return false;
}