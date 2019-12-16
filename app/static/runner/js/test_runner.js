var TestLogger = (function () {
    var _enabled = true;
    var write = function (message) {
        if (_enabled)
            console.log(message);
    };

    var enableLog = function (enable) {
        _enabled = enable === true;
    };

    return {
        write: write,
        enableLog: enableLog
    }
})();

var TestRunner = (function () {
    var _assessment_guid, _assessment_enroll_guid, _testset_id, _testlet_id, _stage_data, _session,
        _question_no;
    var _item_info = [], _last_question_no = 0;
    var _renderedCb, _responseProcessedCb, _responseProcessingCb, _toggleFlaggedCb, _goToQuestionNo, _nextStage,
        _finishTest, _session_cb;
    var _duration_timer, _start_time, _test_duration_minutes;
    var init = function ($container, options) {
        _assessment_guid = options.assessment_guid;
        _testset_id = options.testset_id;
        _testlet_id = options.testlet_id;
        _session = options.session;
        _session_cb = options.session_cb;
        _stage_data = [];
        if (!_session) {
            createSession();
            setCookie('question_no', 1);
        }
        ItemRunner.init($container, {
            mode: 'assessment',
            testset_id: _testset_id,
            renderedCb: _renderedCb,
            responseProcessingCb: _responseProcessingCb,
            responseProcessedCb: _responseProcessedCb,
            toggleFlaggedCb: _toggleFlaggedCb
        });
        var summary_btn = $('.header-summary');
        summary_btn.on('click', function () {
            $('.tools-ruler').hide();
            $('.tools-protractor').hide();
            if ($(this).hasClass('summary-open')) {
                _toggleSummary(false);
            } else {
                _toggleSummary(true);
            }
        });
        $('.filter-btn-group .filter-btn').on('click', function () {
            $('.filter-btn-group .filter-btn').removeClass('active');
            $(this).addClass('active');
            _drawSummary();
        });
        var btn = $('.footer-next-btn');
        btn.on('click', function () {
            $('.tools-ruler').hide();
            $('.tools-protractor').hide();
            ItemRunner.processResponse();
        });
        btn = $('.footer-back-btn');
        btn.on('click', function () {
            $('.tools-ruler').hide();
            $('.tools-protractor').hide();
            _goToQuestionNo(_question_no - 1);
        });
        btn = $('.footer-flag-btn');
        btn.on('click', function () {
            ItemRunner.toggleFlag();
        });
        btn = $('.header-tools-ruler-btn');
        btn.on('click', function () {
            $('.tools-ruler').toggle();
        });
        btn = $('.header-tools-protractor-btn');
        btn.on('click', function () {
            $('.tools-protractor').toggle();
        });
        $('#stageModal .next-stage').on('click', function () {
            _nextStage();
        });
        $('#finishModal .finish-test').on('click', function () {
            _finishTest();
        });
        document.addEventListener("contextmenu", function(e){
            e.preventDefault();
        }, false);
    };
    var _setDurationTimer = function () {
        var seconds_past = moment().unix() - _start_time;
        var minutes_remained = _test_duration_minutes - Math.floor(seconds_past / 60);
        if (minutes_remained < 0) {
            if (_duration_timer)
                clearInterval(_duration_timer);
            _duration_timer = null;
            return;
        }
        var hours = Math.floor(minutes_remained / 60);
        if (hours > 9) hours = "" + hours;
        else hours = "0" + hours;
        var minutes = minutes_remained % 60;
        if (minutes > 9) minutes = "" + minutes;
        else minutes = "0" + minutes;
        $('.timer-display .hours .number').html(hours);
        $('.timer-display .minutes .number').html(minutes);
    };
    var _startDurationTimer = function (start_time, test_duration_minutes) {
        _start_time = start_time;
        _test_duration_minutes = test_duration_minutes;
        _setDurationTimer();
        if (_duration_timer)
            clearInterval(_duration_timer);
        _duration_timer = setInterval(_setDurationTimer, 1000);
    };

    var _setItemInfo = function (question_no, data) {
        _item_info[question_no] = _item_info[question_no] || {};
        var info = _item_info[question_no];
        $.extend(info, data);
        if (question_no > _last_question_no) _last_question_no = question_no;
    };
    var _getItemInfo = function (question_no) {
        _item_info[question_no] = _item_info[question_no] || {};
        return _item_info[question_no];
    };

    var _toggleSummary = function (show) {
        var $summary_btn = $('.header-summary');
        if (show) {
            $summary_btn.addClass('summary-open');
            _drawSummary();
            $('.summary-container').show();
            $('.item-container').hide();
            $('.item-footer .footer-flag-btn').hide();
        } else {
            $summary_btn.removeClass('summary-open');
            $('.summary-container').hide();
            $('.item-container').show();
            $('.item-footer .footer-flag-btn').show();
        }
    };
    var _toggleFlagged = function (flagged) {
        var $flag_btn = $('.item-footer .footer-flag-btn');
        var $flag_txt = $('.item-footer .footer-flag-btn span');
        if (flagged) {
            $flag_btn.addClass('flagged');
            $flag_txt.html('Unflag');
        } else {
            $flag_btn.removeClass('flagged');
            $flag_txt.html('Flag');
        }
    };

    function _hasAnswer(answer) {
        if (typeof answer === "string")
            answer = [answer];
        for (var i = 0; i < answer.length; i++) {
            if (answer[i] !== '')
                return true;
        }
        return false;
    }

    var _drawSummary = function () {
        var i;
        var $question_summary = $('.question-list-summary');
        $question_summary.empty();
        var filter = $('.filter-btn-group .filter-btn.active').data('filter');

        var all_cnt = 0, answered_cnt = 0, not_answered_cnt = 0, not_read_cnt = 0, flagged_cnt = 0;
        for (i = 1; i <= _last_question_no; i++) {
            var btn = $('<button>');
            var itm = _getItemInfo(i);
            var filtered = (filter === 'all');
            all_cnt++;
            btn.html(itm.question_no);

            if (itm.is_flagged) {
                btn.addClass('flagged');
                flagged_cnt++;
                if (filter === 'flagged')
                    filtered = true;
            }
            if (!itm.is_read) {
                btn.addClass('not_read');
                not_read_cnt++;
                if (filter === 'not_read')
                    filtered = true;
            } else {
                if (_hasAnswer(itm.saved_answer)) {
                    btn.addClass('answered');
                    answered_cnt++;
                    if (filter === 'answered')
                        filtered = true;
                } else {
                    btn.addClass('not_answered');
                    not_answered_cnt++;
                    if (filter === 'not_answered')
                        filtered = true;
                }
            }
            if (itm.is_read && filtered) {
                btn.on('click', function () {
                    _goToQuestionNo(parseInt($(this).html()));
                });
            }
            if (filtered)
                btn.addClass('filtered');
            $question_summary.append(btn);
        }
        $('.filter-btn.all span').html(all_cnt);
        $('.filter-btn.answered span').html(answered_cnt);
        $('.filter-btn.not_answered span').html(not_answered_cnt);
        $('.filter-btn.not_read span').html(not_read_cnt);
        $('.filter-btn.flagged span').html(flagged_cnt);
    };

    var createSession = function () {
        var data = {
            assessment_guid: _assessment_guid,
            testset_id: _testset_id,
            student_ip: $('input[name="student_ip"]').val(),
            start_time: Math.floor(Date.now() / 1000)
        };
        $.ajax({
            url: '/api/session',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(data),
            complete: function () {
            },
            success: function (response) {
                var rsp_data = response.data || {};
                _session = rsp_data.session;

                if (_session_cb) {
                    _session_cb(_session);
                }
            }
        });
    };
    var startTest = function () {
        var question_no = getCookie('question_no') || 1;
        var data = {
            session_id: _session,
            question_no: question_no
        };
        $.ajax({
            url: '/api/start',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(data),
            complete: function () {
            },
            success: function (response) {
                var rsp_data = response.data || {};
                _session = rsp_data.session;

                var question_no = rsp_data.next_question_no;
                for (var i = 0; i < rsp_data.new_questions.length; i++) {
                    var q = rsp_data.new_questions[i];
                    var data = {
                        question_no: q.question_no,
                        item_id: q.item_id,
                        marking_id: q.marking_id,
                        is_flagged: q.is_flagged,
                        is_read: q.is_read,
                        saved_answer: q.saved_answer
                    };
                    _setItemInfo(q.question_no, data);
                }

                _goToQuestionNo(question_no);
                _startDurationTimer(rsp_data.start_time, rsp_data.test_duration);
            }
        });
    };

    _goToQuestionNo = function (question_no) {
        if (question_no > _last_question_no) {
            TestLogger.write("_goToItemNo : question_no > _last_question_no");
            return;
        }
        _question_no = question_no;
        var info = _getItemInfo(question_no);
        ItemRunner.setItemId(info.item_id);
        ItemRunner.setItemNo(info.question_no);
        ItemRunner.setMarkingId(info.marking_id);
        ItemRunner.setSession(_session);
        ItemRunner.setItemInfo(_getItemInfo(question_no));
        ItemRunner.getRendered();
    };

    _renderedCb = function (question_no) {
        $('.question-number').html(question_no);
        if (question_no === 1) {
            $('.footer-back-btn').hide();
        } else {
            $('.footer-back-btn').show();
        }
        _toggleSummary(false);
        var info = _getItemInfo(question_no);
        _toggleFlagged(info.is_flagged);
        setCookie('question_no', question_no, 0);
    };
    _responseProcessedCb = function (rsp_data) {
        _setItemInfo(rsp_data.question_no, {'saved_answer': rsp_data.saved_answer});
        if (rsp_data.status === 'in_testing' && rsp_data.next_item_id) {
            var question_no = rsp_data.next_question_no;
            var data = {
                question_no: question_no,
                item_id: rsp_data.next_item_id,
                marking_id: rsp_data.next_marking_id,
                is_flagged: rsp_data.is_flagged,
                is_read: rsp_data.is_read,
                saved_answer: rsp_data.next_saved_answer
            };
            _setItemInfo(question_no, data);
            _goToQuestionNo(question_no);
        } else {
            if (rsp_data.status === 'stage_finished') {
                _testlet_id = rsp_data.testlet_id;
                _session = rsp_data.session;
                _question_no = rsp_data.question_no;
                $('#stageModal .modal-body').html(rsp_data.html);
                $('#stageModal').modal('show');
            } else if (rsp_data.status === 'test_finished') {
                _session = rsp_data.session;
                $('#finishModal .modal-body').html(rsp_data.html);
                $('#finishModal').modal('show');
            }
        }
    };

    _responseProcessingCb = function (question_no, response) {
        // var has_response = ItemHandlers.hasResponse(response);
        // _setItemInfo(question_no, {answer: response});
    };

    _toggleFlaggedCb = function (question_no, flagged) {
        _setItemInfo(question_no, {is_flagged: flagged});
        _toggleFlagged(flagged);
    };

    _nextStage = function () {
        var data = {
            session: _session,
            testlet_id: _testlet_id,
            question_no: _question_no
        };
        $.ajax({
            url: '/api/next_stage',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(data),
            complete: function () {
                $('#stageModal').modal('hide');
            },
            success: function (response) {
                var rsp_data = response.data || {};
                var question_no = rsp_data.next_question_no;
                _session = rsp_data.session;
                for (var i = 0; i < rsp_data.new_questions.length; i++) {
                    var q = rsp_data.new_questions[i];
                    var data = {
                        question_no: q.question_no,
                        item_id: q.item_id,
                        marking_id: q.marking_id,
                        is_flagged: q.is_flagged,
                        is_read: q.is_read,
                        saved_answer: q.saved_answer
                    };
                    _setItemInfo(q.question_no, data);
                }
                _goToQuestionNo(question_no);
            }
        });
    };

    _finishTest = function () {
        var data = {
            session: _session
        };
        $.ajax({
            url: '/api/finish',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(data),
            complete: function () {
                $('#finishModal').modal('hide');
            },
            success: function (response) {
                var data = response.data;
                window.location = data.redirect_url + '?session=' + _session;
            }
        });
    };
    var setCookie = function (cname, cvalue, exdays) {
        var d = new Date();
        d.setTime(d.getTime() + (exdays * 24 * 60 * 60 * 1000));
        var expires = "expires=" + d.toUTCString();
        if (exdays === 0)
            expires = '';
        document.cookie = cname + "=" + cvalue + ";" + expires + ";path=/";
    };

    var getCookie = function g(cname) {
        var name = cname + "=";
        var ca = document.cookie.split(';');
        for (var i = 0; i < ca.length; i++) {
            var c = ca[i];
            while (c.charAt(0) === ' ') {
                c = c.substring(1);
            }
            if (c.indexOf(name) === 0) {
                return c.substring(name.length, c.length);
            }
        }
        return "";
    };

    return {
        init: init,
        startTest: startTest,
        goToItemNo: _goToQuestionNo
    };
})();

$(function () {
    // Assign Draggable and Rotatable
    $('.tools-ruler').draggable({
        cancel: ".ui-rotatable-handle"
    }).rotatable(
        {handleOffset: {top: 10, left: 270}}
    );
    $('.tools-protractor').draggable({
        cancel: ".ui-rotatable-handle"
    }).rotatable(
        {handleOffset: {top: 10, left: 193}},
        {rotationCenterOffset: {top: 205, left: 205}});
});