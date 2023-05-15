var assessment_id, ids, names, grade, subjects, current_ids;
var g_flag = true;// set false when testsets not found
var _id;
var is_leave = false; // set true when "Save Testsets" button enabled

$(function () {
    $("#sortable").sortable({
        placeholder: "ui-state-highlight",
        change: function (event, ui) {
            $('#save_items').removeAttr("disabled");
            is_leave = true;
        }
    });
    $("#sortable").disableSelection();
});

window.addEventListener('beforeunload', function (e) {
    if (is_leave) {
      // Cancel the event
      e.preventDefault();
      // Chrome requires returnValue to be set
      e.returnValue = 'Are you sure to leave without save changes?';
    }
});

$(document).ready(function () {
    /**
     * Initial setup processing:
     *  Set checked attr on the first radio object
     *  Set the value to plan_id html hidden obj for Clone, Edit, Delete
     *  Rendering Assessment Detail span objects with checked assessment
     *  Disable <Save Testsets> button
     *  */
    $radio = $('input[name="r_tl"]');
    $radio.each(function () {
        $(this).prop('checked', true);
        return false;
    });
    $checked_radio = $('input[name="r_tl"]:checked');
    _id = $checked_radio.val();
    $('input[name="assessment_id"]').val(_id);
    invokeTestsetList($checked_radio);
    $('#save_testsets').attr("disabled", "disabled");

    /**
     * Event Handler:
     *      Radio : $('input[name="r_tl"]') click
     *      Button : <Save Testsets>, <Add Testsets>, <New>, <Edit> click
     *          - call function renderUrlDocument() from csedu_common.js
     * */
    // $('input[name="r_tl"]') Radio click
    $radio.click(function () {
        _id = $(this).val();
        $checked_radio = $(this);
        $('input[name="assessment_id"]').val(_id);
        $('#save_assessments').attr("disabled", "disabled");
        invokeTestsetList(this);
    });

    // <Save Testsets> button click
    $('#save_testsets').click(function () {
        var flag = true;
        var testsets = getListedTestsetIds();
        is_leave = false;

        if (window.g_flag != null)
            flag = window.g_flag;
        $('#ordered_ids').val(testsets);
        $('#ordered_assessment_id').val(_id);
        if (flag)
            $('#item_form').submit();
    });

    // <Add Testsets> button click
    $('#add_testsets').click(function () {
        $('#save_testsets').removeAttr("disabled");
        is_leave = true;
        renderUrlDocument(this, 'dataModalSub');
    });

    // <New> button click
    $('button[name="modalButtonNew"]').click(function () {
        renderUrlDocument(this, 'dataModalMedium', 0); //set id 0 for new
    });

    // <Edit> button click
    $('button[name="modalButtonEdit"]').click(function () {
        if($(this).closest('tr').prev().find('td:eq(0) > input').length > 0){
            if(!$(this).closest('tr').prev().find('td:eq(0) > input').is(':checked')){
			    $(this).closest('tr').prev().find('td:eq(0) > input').prop('checked', true).trigger("click");
            }
		}
        renderUrlDocument(this, 'dataModalMedium');
    });

    /**
     * Modal dataModalSub: rendering search details page
     * Set relevant data to share between parent and modal windows
     */
    $("#dataModalSub").on("hidden.bs.modal", function () {
        ids = window.ids;
        names = window.names;
        grade = window.grade;
        subjects = window.subjects;
        arr_ids = ids.slice(1).split(",");
        arr_names = names.slice(1).split(",");
        arr_grade = grade.slice(1).split(",");
        arr_subjects = subjects.slice(1).split(",");

        for (i = 0; i < arr_ids.length; i++) {
            if (arr_ids[i].length != 0) {
                drawTestsetList(arr_ids[i], arr_names[i], arr_grade[i], arr_subjects[i]);
            }
        }
    });

    $("#dataModalSub").on("show.bs.modal", function () {
        window.ids = '';
        window.names = '';
        window.grade = '';
        window.subjects = '';
        window.current_ids = getListedTestsetIds('add');
    });

    /**
     * Function getListedTestsetIds(): Read sortable objects and get testset id list
     * @param mode: 'add' when $("#dataModalSub").on("show")
     * @returns {string}: set window.current_ids
     */
    function getListedTestsetIds(mode) {
        var testsets = '';
        $('#sortable > li > span').each(function () {
            var $span = $(this);
            if (($span.text().search('No Testsets found.') != -1) && (mode != 'add')) {
                alert("Please add testsets first");
                window.g_flag = false;
            } else {
                var testset = $span.text().split(" ");
                testsets = testsets + ',' + testset[0];
                window.g_flag = true;
            }
        });
        return testsets;
    }

    /**
     * Function invokeTestsetList(): rendering assessment-testsets information
     * @param obj: obsolete object reference but still keep for next development
     * @returns {boolean}
     */
    function invokeTestsetList(obj) {
        var $btn = $('#search_item');
        var data = {
            id: _id
        };
        if (data.id == null) return false;

        $.ajax({
            method: 'GET',
            url: '/api/testsets/',
            data: data,
            beforeSend: function () {
                $btn.attr('disabled', true);
            },
            success: function (data) {
                var list = document.getElementById("sortable");

                while (list.hasChildNodes())
                    list.removeChild(list.childNodes[0]);
                var i = 0;

                if (data.length == 0) {
                    drawTestsetList();
                } else {
                    data.forEach(function (item) {
                        // item[0]: id, item[1]: name, item[2]: grade, item[3]: subject
                        drawTestsetList(item[0], item[1], item[2], item[3]);
                        i++;
                    });
                }
            }
        });
    }

    /**
     * Function drawTestsetList(): called by invokeTestsetList() and rendering HTML objects for testsets
     * @param id
     * @param name
     * @param grade
     * @param subject
     */
    function drawTestsetList(id, name, grade, subject) {
        var list = document.getElementById("sortable");
        var flag = false;
        // initiate when the first item including from modal box
        if (list.innerText.search('No Testsets found.') != -1) {
            list.removeChild(list.childNodes[0]);
        }
        var n = document.createElement("li");
        var span = document.createElement("span");
        span.className = "badge badge-light";

        var tn='';
        if (id == null && name == null && grade == null && subject == null) {
            // tn = document.createTextNode('No Testsets found.');
            flag = true;
            return true;
        } else {
            tn = document.createTextNode(id + '  ' + name + '  ' + grade + '  ' + subject)
            span.appendChild(tn);
        }

        // Item deletion
        var span2 = document.createElement("a");
        span2.id = 'delete' + id;
        var i2 = document.createElement("i");
        i2.className = "cui-trash";
        span2.appendChild(i2);

        // Item Detail Modal box invoke
        var span3 = document.createElement("a");
        span3.id = 'detail' + id;
        var i3 = document.createElement("i");
        i3.className = "fas fa-eye";
        span3.appendChild(i3);

        n.appendChild(span);
        if (!flag) {   // not shown delete/info icon when item not-existing
            n.appendChild(span2);
            n.appendChild(span3);
        }
        list.appendChild(n);
        $('#delete' + id).attr("onclick", "$(this).parent().remove();$('#save_testsets').removeAttr('disabled');is_leave = true");
        $('#detail' + id).attr("onclick", "invokeModalTestset(" + id + ")");
        $('#detail' + id).attr("data-toggle", "modal");
        $('#detail' + id).attr("data-target", "#dataModal");
    }

    function invokeModalTestset(id) {
        var url = '/testset/' + id + '/preview';
        $.get(url, function (data) {
            $('#dataModal .modal-content').html(data);
            $('#dataModal').modal();
        });
    }
});


