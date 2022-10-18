function search_assessment(year, test_type, marker_name) {
    if(isNaN(year)) return false;
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

const uploadFile = (files, writing_id, student_user_id, marking_writing_id, student_id) => {
  const API_ENDPOINT = "/api/writing_marking_list/responses/file/" + writing_id;
  const request = new XMLHttpRequest();
  const formData = new FormData();

  request.open("POST", API_ENDPOINT, true);
  request.onreadystatechange = () => {
    if (request.readyState === 4 && request.status === 200) {
      let uploaded_files = JSON.parse(request.responseText).data.data;
        let tr = $('input[data-marking-writing-id="'+marking_writing_id+'"]').closest('tr');
        if(uploaded_files.length > 1){
            let htm = '';
            htm += '<a name="download1" class="badge badge-primary" data-marking_writing_id="'+marking_writing_id+'" href="/writing/writing_marking_list/download/'+marking_writing_id+'/'+student_user_id+'">zip</a>';
            tr.find('td:eq(7)').html(htm);
            tr.find('td:eq(5)').html('Y');
        }else{
            let extension = uploaded_files[0].substring(uploaded_files[0].indexOf('.'));
            let htm = '';
            htm += '<span class="btn btn-light btn-square btn-sm" data-toggle="tooltip" data-placement="top" data-original-title="file download" title="file download">';
            htm += '<a name="download2" href="/api/userdata/writing/'+marking_writing_id+'/'+student_user_id+'/'+ uploaded_files[0] +'" data-marking_writing_id="'+marking_writing_id+'" download="writing_'+marking_writing_id+'_'+student_id + extension +'"><i class="fas fa-file-download" style="color: #ff0000"></i></a>"';
            htm += '</span>';
            tr.find('td:eq(7)').html(htm);
            tr.find('td:eq(5)').html('Y');
        }
    } else if (request.readyState === 4 && request.status === 400) {
      alert(JSON.parse(request.responseText).message);
    }
  };
  if (files.length > 0) {
    //This fileName and fileType are just for response checker in PHP.
    let fileNames = [];
    for (var i=0; i<files.length; i++) {
        formData.append('files', files[i]);
    }
  }
  formData.append('student_user_id', student_user_id);
  formData.append('writing_text', '');
  formData.append('has_files', 'true');

  request.send(formData);
};

$(function(){
    $('#w_table').DataTable( {
        searching: false,
        info: false,
        paging:false,
        "orderClasses": false,
        "order": [[ 0, 'desc' ],[ 3, 'desc' ]],
        "columnDefs": [{
            "targets"  : 8,
            "orderable": false
        }]
    });

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

    $('body').on('click','a[name=download1], a[name=download2]', function(){
        if($('#apply_download').is(':checked')){
            if($(this).closest('td').find('div[name="download_mark"]').length==0) {
                let btn = $(this);
                $.post('/api/writing_marking_list/downloaded', { 'id': $(this).attr('data-marking_writing_id') },
                    function() {
                        btn.closest('td').append(' <div name="download_mark" class="d-inline-block"><i class="fas fa-check"></i></div>');
                    }).fail(function(jqxhr, settings, ex) {}
                );
            }
        }
    });

    $('#w_table_wrapper, input[type="file"]').get(0).addEventListener("change", event => {
      const files = event.target.files;
      uploadFile(files, $(event.target).data('writing-id'), $(event.target).data('student-user-id'), $(event.target).data('marking-writing-id'), $(event.target).data('student-id'));
    });

    $('body').on('click', '#w_table_wrapper button', function(){
        $(this).parent().find('input[type="file"]').click();
    });
});

function validateForm(){
    return false;

}