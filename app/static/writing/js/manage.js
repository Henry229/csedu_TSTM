
$(document).ready(function () {
    $("#w_table").hide();

});

/**
 * Function searchWritings(): search item list of writings
 * @returns {boolean}
 */
function searchWritings(assessment_guid) {
    var $btn = $('#search_item');
    var data = {
        assessment_guid: assessment_guid,
        student_id: $("#select_student option:selected").val()
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
            i=0;
            result.forEach(function (item) {
                drawItemList(data.student_id, item.assessment_enroll_id, item.assessment_name,
                            item.item_id, item.marking_id, item.marking_writing_id, item.start_time);
                i++;
            });
            if (i==0) {
                $("#w_table").hide();
            } else {
                $("#w_table").show();
            }
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
 * @returns {boolean}
 */
function drawItemList(student_id, assessment_enroll_id, assessment_name,
                            item_id, marking_id, marking_writing_id, start_time) {
    var tbody = document.getElementById("w_table_body");
    var row = tbody.insertRow(0);
    var cell1 = row.insertCell(0);
    var cell2 = row.insertCell(1);
    var cell3 = row.insertCell(2);
    var cell4 = row.insertCell(3);
    var cell5 = row.insertCell(4);
    var cell6 = row.insertCell(5);

    // Item Detail Modal box invoke
    var span_item = document.createElement("a");
    span_item.id = 'detail' + item_id;
    span_item.innerText=item_id+' ';
    var i1 = document.createElement("i");
    i1.className = "fas fa-eye";
    span_item.appendChild(i1);

    // Marking for writing link
    var span_marking = document.createElement("a");
    span_marking.id = 'marking' + marking_writing_id;
    var anchor = document.createElement("a");
    anchor.href = '/writing/marking/'+marking_writing_id+'/'+student_id;
    anchor.target = '_blank';
    var i2 = document.createElement("i");
    i2.className = "icons cui-task";
    anchor.appendChild(i2);
    span_marking.appendChild(anchor);

    cell1.innerHTML = assessment_enroll_id;
    cell2.innerHTML = assessment_name;
    cell3.innerHTML = start_time;
    cell4.appendChild(span_item);
    cell5.innerHTML = marking_id;
    cell6.appendChild(span_marking);

    $('#detail' + item_id).attr("onclick", "invokeModalItem(" + item_id + ")");
    $('#detail' + item_id).attr("data-toggle", "modal");
    $('#detail' + item_id).attr("data-target", "#dataModal");
}

function invokeModalItem(id) {
    var url = '/item/' + id + '/preview';
    $.get(url, function (data) {
        $('#dataModal .modal-content').html(data);
    });
    $('#dataModal .modal-content').html("Loading... Try again if data not shown");
}