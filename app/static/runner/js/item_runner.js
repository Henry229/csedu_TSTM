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
    var _review_mode = false;
    var _renderedCb, _responseProcessingCb, _responseProcessedCb, _responseProcessedSimpleCb,
      _toggleFlaggedCb, _sessionErrorCb,
    _disableSubmitResponse;

    var init = function ($container, options) {
        _$container = $container;
        _mode = options.mode || _mode;
        _assessment_enroll_id = options.assessment_enroll_id || _assessment_enroll_id;
        _testset_id = options.testset_id || _testset_id;
        _review_mode = options.review_mode || false;
        _renderedCb = options.renderedCb || emptyCb;
        _responseProcessingCb = options.responseProcessingCb || emptyCb;
        _responseProcessedCb = options.responseProcessedCb || emptyCb;
        _responseProcessedSimpleCb = options.responseProcessedSimpleCb || emptyCb;
        _toggleFlaggedCb = options.toggleFlaggedCb || emptyCb;
        _sessionErrorCb = options.sessionErrorCb || emptyCb;
        _disableSubmitResponse = options.disableSubmitResponse || emptyCb;
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

    var setReviewMode = function (review_mode) {
        _review_mode = review_mode;
    }

    var _calculateSize = function() {
      // reading with a long description
      //Up and Down
      var col_12s = $('.item-body .grid-row .col-12');
      if (col_12s.length > 1 ) {
          // var item_body_height = $('.item-body')[0].clientHeight;
          // var first_row_height = col_12s[0].clientHeight;
          // If the description occupies more than 80%
          // if (first_row_height / item_body_height > 0.8) {
          //     $(col_12s[0]).addClass('with-scroll');
          // }
          // image 가 있는 경우 dom 의 크기가 이미지를 다 불러온 후에 변경이 되어 크기를 계산할 수 없다
          // if there is a question and answers in this div, skip addClass
         if($(col_12s[0]).children("div").attr("data-serial") !== undefined){
              $(col_12s[0]).addClass('with-scroll');
          }
      }
      var col_6s = $('.item-body .grid-row .col-6');
      if (col_6s.length > 1 ) {
          if($(col_6s[0]).children("div").attr("data-serial") !== undefined) {
              $(col_6s[0]).addClass('with-scroll');
          }
      }
    };

    var _addJWPlayer = function (media_url) {
        if (!window.jwplayer) {
            setTimeout(_addJWPlayer, 400, media_url);
            return;
        }
        var a_tags = _$container.find('a');
        var jw_element = null;
        var player_file = '';
        for (var i=0; i< a_tags.length; i++) {
            if (a_tags[i].href.indexOf('jwplayer-id') !== -1) {
                player_file = a_tags[i].href;
                jw_element = $(a_tags[i]);
                break;
            }
        }
        if (jw_element === null) return;
        var parent_div = jw_element.parents('div')[0];
        parent_div.id = 'jwPlayer';
        $(parent_div).empty();
        $(parent_div).show();
        var media_info = _parse_media_info(player_file);
        var playerInstance = jwplayer("jwPlayer").setup({
            playlist: media_url,
            height: 360,
            width: 640,
            skin: {
                name: "csedu"
            },
            autostart: media_info.auto_play ? 'viewable': false
        });
        playerInstance.on('ready', function () {
            var caption_list = playerInstance.getCaptionsList();
            if (media_info.show_caption && caption_list.length > 1) {
                playerInstance.setCurrentCaptions(1);
            }
            else if (caption_list.length > 1) {
                playerInstance.setCurrentCaptions(0);
            }
        });
    };
    var _hideJWPlayer = function (container) {
        var a_tags = container.find('a');
        var jw_element = null;
        var player_file = '';
        for (var i=0; i< a_tags.length; i++) {
            if (a_tags[i].href.indexOf('jwplayer-id') !== -1) {
                player_file = a_tags[i].href;
                jw_element = $(a_tags[i]);
                break;
            }
        }
        if (jw_element === null) return;
        var parent_div = jw_element.parents('div')[0];
        $(parent_div).hide();
    };
    var _parse_media_info = function (media_info_string) {
        var info = {media_id: '', auto_play: false, show_caption: true};
        var media_info = (media_info_string.split('jwplayer-id/')[1]).split('?');
        info.media_id = media_info[0];
        if (media_info.length>1) {
            var params = media_info[1].split('&');
            for (var i=0; i<params.length; i++) {
                if (params[i].indexOf('auto_play=') === 0) {
                    info.auto_play = params[i].split('=')[1] === 'on';
                }
                else if (params[i].indexOf('caption=') === 0){
                    info.show_caption = params[i].split('=')[1] !== 'off';
                }
            }
        }
        return info;
    };
    // Left and Right
    var postProcessRendered = function (data) {
        _handler = ItemHandlers.init(_interaction_type, {container: _$container, data: data,
            review_mode: _review_mode});
        if (data.jw_player)
            _addJWPlayer(data.jw_player.media_url);
        if (_mode !== 'preview') {
            _handler.processUI(_item_info.saved_answer);
        }
        if (MathJax)
            MathJax.typeset();
        _calculateSize();
    };

    var drawRendered = function (data) {
        var rendered_html = data.html;
        _$container.empty();
        var div = $(rendered_html);
        if (data.jw_player) {
            _hideJWPlayer(div);
            if (data.jw_player.player_url) {
                _$container.append($('<script src="' + data.jw_player.player_url + '"></script>'));
                window.jwplayer = null;
            }
        }
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
        var url;

        if (_mode === 'assessment') {
            url = '/api/rendered/' + item_id + '?session=' + _session;
        } else if (_mode === 'errornote') {
            url = '/api/errorrun/rendered/' + item_id + '?session=' + _session;
        } else if (_mode === 'peek') {
            url = '/item/' + item_id + '/peek';
        } else {
            url = '/item/' + item_id + '/rendered';
        }

        $.ajax({
            url: url,
            beforeSend: function () {
                _disableSubmitResponse(true);
                _$container.html(loading);
                $('.usage-info-button').hide();
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
                    drawRendered(data);
                    postProcessRendered(data);
                    _renderedCb(_question_no);
                }
                _disableSubmitResponse(false);
            }
        });
    };

    /**
     * Test runner 에서 Next 를 누를 때 입력한 답을 서버에 전달한다.
     *  - File upload 가 있는 때는 response.formData 에 데이터가 있다.
     *    이 경우 우선 processAssessmentFormResponse 로 파일을 업로드 하고, 성공하면 success 에서 processAssessmentResponse 를
     *    실행한다.
     */
    var processResponse = function (callbackFn, callbackData) {
        var response = _handler.getResponse();
        if (response === null) return;
        if (_mode === 'assessment' || _mode === 'errornote') {
            if (response.formData || response.writing_text)
                processAssessmentFormResponse(response, callbackFn, callbackData);
            else
                processAssessmentResponse(response, callbackFn, callbackData);
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

    var processAssessmentResponse = function (response, callbackFn, callbackData) {
        var url = '/api/responses/' + _item_id;
        if (_mode === 'errornote') {
            url = '/api/errorrun/responses/' + _item_id;
        }
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
                _disableSubmitResponse(true);
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
                // _disableSubmitResponse(false);
                if (response.result === 'success') {
                    if (callbackFn) {
                        _responseProcessedSimpleCb(response.data);
                        callbackFn(callbackData);
                    } else if (_responseProcessedCb) {
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
    var processAssessmentFormResponse = function (response, callbackFn, callbackData) {
        var url = '/api/responses/file/' + _item_id;
        if (_mode === 'errornote') {
            url = '/api/errorrun/responses/file/' + _item_id;
        }
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
                _disableSubmitResponse(true);
            },
            complete: function () {

            },
            error: function (jqXHR, textStatus, errorThrown ) {
                _sessionErrorCb(jqXHR);
            },
            success: function (response) {
                if (response.result === 'success') {
                    processAssessmentResponse(response_data, callbackFn, callbackData);
                }
                //_disableSubmitResponse(false);
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
        setReviewMode: setReviewMode,
        getRendered: getRendered,
        processResponse: processResponse,
        toggleFlag: toggleFlag
    }
})();