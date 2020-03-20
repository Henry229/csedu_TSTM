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

function getTestReport(assessment_id, testset_id, num) {
    var select_option = $("#select_"+num+"_student_"+assessment_id+"_"+testset_id+" option:selected");
    var select_option_text = select_option.text();
    var n = select_option_text.indexOf(":");
    var assessment_enroll_id = select_option_text.substring(1,n);
    var url = '/report/ts/'+assessment_enroll_id+'/'+assessment_id+'/'+testset_id+'/'+select_option.val();
    $('a[name="btnTestReport"]').attr("href",url);
}

function getAssessmentReport(assessment_id,num) {

    var url = '/report/student/set/'+assessment_id+'/'+$("#select_"+num+"_student_"+assessment_id+" option:selected").val();
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

function reset_test() {

    // $.ajax({
    //     url: '/api/gen_report/',
    //     method: 'POST',
    //     beforeSend: function () {
    //
    //     },
    //     complete: function () {
    //
    //     },
    //     success: function (response) {
    //         console.log(response);
    //         $("#status").show();
    //         $("#status").html("Report generated successfully").fadeOut(3000, function () {
    //             $(this).hide()
    //         });
    //     }
    // });
}