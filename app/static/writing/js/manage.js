$(function () {
    $('[data-toggle="tooltip"]').tooltip()
});

$(document).ready(function () {
    $("#w_table").hide();
    $("#status").hide();

    $('a[name="modalButtonAssign"]').click(function () {
        var url = $(this).attr("href");
        $.get(url, function (data) {
            $('#dataModalMedium .modal-content').html(data);
        });
        $('#dataModalMedium .modal-content').html("Loading... Try again if data not shown");
    });

    $("#dataModalSub").on("hidden.bs.modal", function () {
        $("#w_table").show();
    });
});

/**
 * Function searchWritings(): search item list of writings
 * @returns {boolean}
 */
function searchWritings(assessment_guid,id,testset_id) {
    var $btn = $('#search_item');
    var data = {
        assessment_guid: assessment_guid,
        testset_id: testset_id,
        student_user_id: $("#select_student"+"_"+id+" option:selected").val()
    };
    if (data.assessment_guid == null) return false;
    $.ajax({
        method: 'GET',
        url: '/api/writing_item_list/',
        data: data,
        beforeSend: function () {
            $btn.attr('disabled', true);
        },
        complete: function () {
            $btn.attr('disabled', false);
        },
        success: function (result) {
            i = 0;
            removeItemList();
            result.forEach(function (item) {
                drawItemList(data.student_user_id, item.assessment_enroll_id, item.assessment_name,
                    item.item_id, item.marking_id, item.marking_writing_id, item.start_time,
                    item.is_candidate_file, item.is_marked);
                i++;
            });

            if (i == 0) {
                drawItemList();
            }
            $("#w_table").show();
        }
    });
}

/**
 * Function drawItemList(): draw writing item list into table #tab_writing_items
 * @param assessment_enroll_id
 * @param assessment_name
 * @param item_id
 * @param marking_id
 * @param marking_writing_id
 * @param start_time
 * @param is_candidate_file
 * @param is_marked
 * @returns {boolean}
 */
function drawItemList(student_user_id, assessment_enroll_id, assessment_name,
                      item_id, marking_id, marking_writing_id, start_time,
                      is_candidate_file, is_marked) {
    var tbody = document.getElementById("w_table_body");
    var row = tbody.insertRow(0);
    var cell1 = row.insertCell(0);
    if ((student_user_id == null) && (assessment_enroll_id == null)) {
        cell1.colSpan = 8;
        cell1.innerHTML = "No data found.";
        return true;
    }
    var cell2 = row.insertCell(1);
    var cell3 = row.insertCell(2);
    var cell4 = row.insertCell(3);
    var cell5 = row.insertCell(4);
    var cell6 = row.insertCell(5);
    var cell7 = row.insertCell(6);
    var cell8 = row.insertCell(7);

    // Item Detail Modal box invoke
    var span_item = document.createElement("a");
    span_item.id = 'detail' + item_id;
    span_item.innerText = item_id + ' ';
    var i1 = document.createElement("i");
    i1.className = "fas fa-eye";
    span_item.appendChild(i1);

    var span_marking = document.createElement("span");
    span_marking.id = 'marking' + marking_writing_id;
    span_marking.className = "btn btn-light btn-square btn-sm";
    span_marking.setAttribute("data-toggle", "tooltip");
    span_marking.setAttribute("data-placement", "top");
    span_marking.setAttribute("data-original-title", "link to marking");
    span_marking.setAttribute("title", "link to marking");
    var anchor = document.createElement("a");
    anchor.href = '/writing/marking/' + marking_writing_id + '/' + student_user_id;
    anchor.target = '_blank';
    var i2 = document.createElement("i");
    i2.className = "fas fa-pen-nib";
    i2.style = "color: red";

    anchor.appendChild(i2);
    span_marking.appendChild(anchor);

    var span_report = document.createElement("span");
    span_report = document.createElement("span");
    span_report.id = 'report' + marking_writing_id;
    span_report.className = "btn btn-light btn-square btn-sm";
    span_report.setAttribute("data-toggle", "tooltip");
    span_report.setAttribute("data-placement", "top");
    span_report.setAttribute("data-original-title", "link to report");
    span_report.setAttribute("title", "link to report");

    var anchor = document.createElement("a");
    anchor.href = '/writing/report/' + assessment_enroll_id + '/' + student_user_id + '/' + marking_writing_id;
    anchor.target = '_blank';
    var i3 = document.createElement("i");
    i3.className = "far fa-file-alt";
    i3.style = "color: blue";

    anchor.appendChild(i3);
    span_report.appendChild(anchor);

    var span_report_pdf = document.createElement("span");
    span_report_pdf = document.createElement("span");
    span_report_pdf.id = 'report_pdf' + marking_writing_id;
    span_report_pdf.className = "btn btn-light btn-square btn-sm";
    span_report_pdf.setAttribute("data-toggle", "tooltip");
    span_report_pdf.setAttribute("data-placement", "top");
    span_report_pdf.setAttribute("data-original-title", "link to report pdf");
    span_report_pdf.setAttribute("title", "link to report pdf");

    var anchor = document.createElement("a");
    anchor.href = '/writing/report/' + assessment_enroll_id + '/' + student_user_id + '/' + marking_writing_id + '?type=pdf';
    var i4 = document.createElement("i");
    i4.className = "fas fa-print";
    i4.style = "color: blue";

    anchor.appendChild(i4);
    span_report_pdf.appendChild(anchor);

    cell1.innerHTML = assessment_enroll_id;
    cell2.innerHTML = assessment_name;
    cell3.innerHTML = start_time;
    cell4.appendChild(span_item);
    cell5.innerHTML = marking_id;
    if (is_candidate_file == true)
        cell6.innerHTML = 'Y';
    else
        cell6.innerHTML = 'N';
    if (is_marked == true)
        cell7.innerHTML = 'Y';
    else
        cell7.innerHTML = 'N';
    cell8.appendChild(span_marking);
    cell8.appendChild(span_report);
    cell8.appendChild(span_report_pdf);
    $('#detail' + item_id).attr("onclick", "invokeModalItem(" + item_id + ")");
    $('#detail' + item_id).attr("data-toggle", "modal");
    $('#detail' + item_id).attr("data-target", "#dataModal");
    return true;
}

/**
 * Function removeItemList() : remove all tr under table tbody
 * @returns {boolean}
 */
function removeItemList() {
    var tbody = $('#w_table');
    tbody.find('tbody tr').remove();
    return true;
}

/**
 * Function invokeModalItem() : Item Preview modal dialog when click <eye> icon
 * @param id
 */
function invokeModalItem(id) {
    ItemRunner.init($('#dataModal .modal-content'), {mode: 'preview'});

    $('#dataModal .modal-content').html("Loading... Try again if data not shown");

    ItemRunner.getRendered(id);
}


