$(document).ready(function () {
    $("#w_table").hide();

    $("#dataModalSub").on("hidden.bs.modal", function () {
        $("#w_table").show();
    });
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
            i = 0;
            removeItemList();
            result.forEach(function (item) {
                drawItemList(data.student_id, item.assessment_enroll_id, item.assessment_name,
                    item.item_id, item.marking_id, item.marking_writing_id, item.start_time,
                    item.is_candidate_file,item.is_marked);
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
function drawItemList(student_id, assessment_enroll_id, assessment_name,
                            item_id, marking_id, marking_writing_id, start_time,
                            is_candidate_file,is_marked) {
    var tbody = document.getElementById("w_table_body");
    var row = tbody.insertRow(0);
    var cell1 = row.insertCell(0);
    if ((student_id==null)&&(assessment_enroll_id==null)) {
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
    span_item.innerText=item_id+' ';
    var i1 = document.createElement("i");
    i1.className = "fas fa-eye";
    span_item.appendChild(i1);

    // Marking for writing link
    var span_marking = document.createElement("span");
    span_marking.id = 'marking' + marking_writing_id;
    var i2 = document.createElement("i");
    i2.className = "icons cui-task";
    span_marking.appendChild(i2);

    cell1.innerHTML = assessment_enroll_id;
    cell2.innerHTML = assessment_name;
    cell3.innerHTML = start_time;
    cell4.appendChild(span_item);
    cell5.innerHTML = marking_id;
    if (is_candidate_file==true)
        cell6.innerHTML = 'Y';
    else
        cell6.innerHTML = 'N';
    if (is_marked==true)
        cell7.innerHTML = 'Y';
    else
        cell7.innerHTML = 'N';
    cell8.appendChild(span_marking);
    $('#detail' + item_id).attr("onclick", "invokeModalItem(" + item_id + ")");
    $('#detail' + item_id).attr("data-toggle", "modal");
    $('#detail' + item_id).attr("data-target", "#dataModal");
    $('#marking' + marking_writing_id).attr("onclick", "invokeModalMarking(" + marking_writing_id + ","+student_id+")");
    $('#marking' + marking_writing_id).attr("data-toggle", "modal");
    $('#marking' + marking_writing_id).attr("data-target", "#dataModalSub");
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
    var url = '/item/' + id + '/preview';
    $.get(url, function (data) {
        $('#dataModal .modal-content').html(data);
    });
    $('#dataModal .modal-content').html("Loading... Try again if data not shown");
}

/**
 * Function invokeModalMarking() : Marking for writing modal dialog when click <check> icon
 * @param marking_writing_id
 * @param student_id
 */
function invokeModalMarking(marking_writing_id, student_id) {
    var url = '/writing/marking/'+marking_writing_id+'/'+student_id;
    $.get(url, function (data) {
        $('#dataModalSub .modal-content').html(data);
    });
    $('#dataModalSub .modal-content').html("Loading... Try again if data not shown");
}

// Modal Image Gallery
function onClick(element) {
  document.getElementById("img01").src = element.src;
  document.getElementById("modal01").style.display = "block";
  var captionText = document.getElementById("caption");
  captionText.innerHTML = element.alt;
}
