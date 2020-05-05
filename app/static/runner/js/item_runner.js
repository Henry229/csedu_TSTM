/*
*/
var ItemRunner = (function () {
    var _$container;
    var _handler;
    var _session;
    var _item_id;
    var _flagged = false;
    var _question_no;
    var _item_info = {};
    var _marking_id;
    var _mode = 'assessment';
    var _$preview_score;
    var _interaction_type;
    var _assessment_enroll_id = 0;
    var _testset_id = 0;
    var _renderedCb, _responseProcessingCb, _responseProcessedCb, _toggleFlaggedCb, _sessionErrorCb;

    var init = function ($container, options) {
        _$container = $container;
        _mode = options.mode || _mode;
        _assessment_enroll_id = options.assessment_enroll_id || _assessment_enroll_id;
        _testset_id = options.testset_id || _testset_id;
        _renderedCb = options.renderedCb || emptyCb;
        _responseProcessingCb = options.responseProcessingCb || emptyCb;
        _responseProcessedCb = options.responseProcessedCb || emptyCb;
        _toggleFlaggedCb = options.toggleFlaggedCb || emptyCb;
        _sessionErrorCb = options.sessionErrorCb || emptyCb;
    };
    var emptyCb = function () {

    };
    var setSession = function (session) {
        _session = session;
    };

    var setItemId = function (item_id) {
        _item_id = item_id;
    };

    var setItemNo = function (question_no) {
        _question_no = question_no;
    };

    var setItemInfo = function (item_info) {
        _item_info = item_info;
    };

    var setMarkingId = function (marking_id) {
        _marking_id = marking_id;
    };

    var postProcessRendered = function (data) {
        _handler = ItemHandlers.init(_interaction_type, {container: _$container, data: data});
        if (_mode !== 'preview') {
            _handler.processUI(_item_info.saved_answer);
        }
        if (MathJax)
            MathJax.typeset()
    };

    var drawRendered = function (rendered_html) {
        _$container.empty();
        var div = $(rendered_html);
        _$container.append(div);
        if (_mode === 'preview') {
            div = $('<div class="alert alert-secondary" role="alert">');
            _$container.append(div);
            _$preview_score = div;
        }
    };

    var getRendered = function (item_id) {
        item_id = item_id || _item_id;
        var loading = '<div class="fa-3x" style="margin: auto">\n' +
            '  <i class="fas fa-spinner fa-spin"></i> <span> Getting Test Item....</span>\n' +
            '</div>';
        if (_mode === 'peek') {
            var url = '/item/' + item_id + '/peek';
        } else {
            var url = '/item/' + item_id + '/rendered';
        }

        if (_mode === 'assessment') {
            url = '/api/rendered/' + item_id + '?session=' + _session;
        }
        $.ajax({
            url: url,
            beforeSend: function () {
                _$container.html(loading);
            },
            complete: function () {

            },
            error: function (jqXHR, textStatus, errorThrown ) {
                _sessionErrorCb(jqXHR);
            },
            success: function (response) {
                if (response.result === 'success') {
                    var data = response.data;
                    _item_id = item_id;
                    _interaction_type = data.type;
                    drawRendered(data.html);
                    postProcessRendered(data);
                    _renderedCb(_question_no);
                }
            }
        });
    };

    /**
     * Test runner 에서 Next 를 누를 때 입력한 답을 서버에 전달한다.
     *  - File upload 가 있는 때는 response.formData 에 데이터가 있다.
     *    이 경우 우선 processAssessmentFormResponse 로 파일을 업로드 하고, 성공하면 success 에서 processAssessmentResponse 를
     *    실행한다.
     */
    var processResponse = function () {
        var response = _handler.getResponse();
        if (response === null) return;
        if (_mode === 'assessment') {
            if (response.formData || response.writing_text)
                processAssessmentFormResponse(response);
            else
                processAssessmentResponse(response);
        } else {
            processPreviewResponse(response);
        }
    };

    var processPreviewResponse = function (response) {
        var url = '/item/' + _item_id + '/response';
        var data = {'response': response};
        $.ajax({
            url: url,
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(data),
            beforeSend: function () {
            },
            complete: function () {

            },
            success: function (data) {
                if (data.result === 'success') {
                    if (_mode === 'preview') {
                        _$preview_score.html(data.processed);
                    }
                }
            }
        });
    };

    var processAssessmentResponse = function (response) {
        var url = '/api/responses/' + _item_id;
        var data = {
            'session': _session,
            'question_no': _question_no,
            'marking_id': _marking_id
        };
        if (response.writing_text) {
            data['writing_text'] = response.writing_text;
            delete response.writing_text;
        }
        if (response.fileNames) {
            data['file_names'] = response.fileNames;
            delete response.fileNames;
        }
        data['response'] = response;
        $.ajax({
            url: url,
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(data),
            beforeSend: function () {
                if (_responseProcessingCb) {
                    _responseProcessingCb(_question_no, response);
                }
            },
            complete: function () {

            },
            error: function (jqXHR, textStatus, errorThrown ) {
                _sessionErrorCb(jqXHR);
            },
            success: function (response) {
                if (response.result === 'success') {
                    if (_responseProcessedCb) {
                        _responseProcessedCb(response.data);
                    }
                } else {
                    if (response.message) {
                        $('#errorModal .modal-body').html(response.message);
                        $('#errorModal').modal('show');
                    }
                }
            }
        });
    };

    /**
     * File 을 업로드한다.
     *  - 두 단계 처리:
     *      1. processAssessmentFormResponse 로 formData(file 을 포함한)을 우선 처리한다.
     *      2. 처리가 success 로 나오면 일반적인 데이터를 processAssessmentResponse 보낸다.
     * @param response
     */
    var processAssessmentFormResponse = function (response) {
        var url = '/api/responses/file/' + _item_id;
        var formData = new FormData();
		var response_data = response;
        if (response.formData) {
            formData = response.formData;
    		delete response_data['formData'];
        }
        if (response.writing_text) {
            formData.append('writing_text', response.writing_text);
        }
        if (response.fileNames) {
            formData.append('has_files', "true");
        }

		    formData.append('session', _session);
		    formData.append('marking_id', _marking_id);

        $.ajax({
            url: url,
            type: 'POST',
            dataType: 'json',
			      contentType: false,
			      processData: false,
            data: formData,
            beforeSend: function () {

            },
            complete: function () {

            },
            error: function (jqXHR, textStatus, errorThrown ) {
                _sessionErrorCb(jqXHR);
            },
            success: function (response) {
                if (response.result === 'success') {
                    processAssessmentResponse(response_data);
                }
            }
        });
    };

    var toggleFlag = function () {
        var url = '/api/flag/' + _item_id;
        var data = {
            'flagged': !_flagged,
            'session': _session,
            'question_no': _question_no,
            'marking_id': _marking_id
        };
        $.ajax({
            url: url,
            type: 'PUT',
            contentType: 'application/json',
            data: JSON.stringify(data),
            beforeSend: function () {
            },
            complete: function () {

            },
            success: function (data) {
                if (data.result === 'success') {
                    _flagged = !_flagged;
                    _toggleFlaggedCb(_question_no, _flagged);
                }
            }
        });
    };

    /**
     * 외부에서 사용해야하는 function 을 노출한다.
     */
    return {
        init: init,
        setSession: setSession,
        setItemId: setItemId,
        setItemNo: setItemNo,
        setItemInfo: setItemInfo,
        setMarkingId: setMarkingId,
        getRendered: getRendered,
        processResponse: processResponse,
        toggleFlag: toggleFlag
    }
})();