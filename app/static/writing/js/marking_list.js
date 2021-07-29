function search_assessment(year, test_type, marker_name) {
    data = {
        "year": year,
        "test_type": test_type,
        "marker": marker_name
    }
    var assessment_obj = $('SELECT[name="assessment"]');
    $.ajax({
        url: '/api/writing_search_assessment/',
        method: 'GET',
        data: data,
        beforeSend: function () {
            assessment_obj.empty()
        },
        complete: function () {

        },
        error: function(xhr, status, error) {
            $("#status").show();
            $("#status").html(xhr.responseText).fadeOut(6000, function () {
                $(this).hide();
            });
        },
        success: function (response) {
            // response.data = [{ 'assessment_guid': '...', 'assessment_name': '...', 'testset_id': '...', 'testset_name': '...'},....] }
            response.data.forEach(function (item) {
                assessment_obj.append(
                    $('<option>', {
                        value: item['assessment_id'] + '_' + item['testset_id'],
                        text: item['assessment_name'] + ' : ' + item['testset_name'] + ' v.' + item['testset_version'],
                    })
                );
            });
        }
    });
}

$(function(){
    $('#year, #test_type, #marker_name').change(function(event) {
        event.preventDefault();
        if($(this).val()==''){
          $('select[name="assessment"]').empty();
        }else {
          var year = parseInt($('SELECT[name="year"] option:selected').val());
          var test_type = $('SELECT[name="test_type"] option:selected').val();
          var marker_name = $('#marker_name')==undefined || $('#marker_name')==null ? 0 : $('#marker_name').find(":selected").val();
          search_assessment(year, test_type, marker_name);
        }
    });

    $('#btn_search1').click(function(){
       if($('select[name="assessment"]').val()==undefined || $('select[name="assessment"]').val()==null || $('select[name="assessment"]').val()=='0') return false;
       return true;
    });
});