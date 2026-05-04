/* WorldFork chat UI logic (★ Tier 2 D8 W2) */
/* vanilla JS + fetch, 외부 패키지 0건 */

(function () {
    'use strict';

    // 상태
    let sessionId = null;
    let turnNumber = 0;

    // DOM 요소
    const startBtn = document.getElementById('start-btn');
    const sendBtn = document.getElementById('send-btn');
    const actionInput = document.getElementById('action-input');
    const messagesEl = document.getElementById('messages');
    const welcomeEl = document.getElementById('welcome');
    const chatEl = document.getElementById('chat');
    const metricsEl = document.getElementById('metrics');
    const sessionStatusEl = document.getElementById('session-status');
    const turnCounterEl = document.getElementById('turn-counter');

    // Metrics 요소
    const mMechanical = document.getElementById('m-mechanical');
    const mTruncated = document.getElementById('m-truncated');
    const mScore = document.getElementById('m-score');
    const mVerify = document.getElementById('m-verify');
    const mLocation = document.getElementById('m-location');

    // ===== UI 헬퍼 =====

    function addMessage(content, type) {
        const msgEl = document.createElement('div');
        msgEl.className = 'message ' + type;

        const labelEl = document.createElement('div');
        labelEl.className = 'message-label';
        labelEl.textContent = type === 'user' ? '플레이어' :
                              type === 'gm' ? 'GM' :
                              type === 'system' ? '시스템' : '오류';
        msgEl.appendChild(labelEl);

        const contentEl = document.createElement('div');
        contentEl.className = 'message-content';
        contentEl.textContent = content;
        msgEl.appendChild(contentEl);

        messagesEl.appendChild(msgEl);
        msgEl.scrollIntoView({ behavior: 'smooth', block: 'end' });
    }

    function updateMetrics(data) {
        // Mechanical
        if (data.mechanical_passed === true) {
            mMechanical.textContent = '✅ 통과';
            mMechanical.className = 'success';
        } else if (data.mechanical_passed === false) {
            mMechanical.textContent = '❌ 실패';
            mMechanical.className = 'error';
        }

        // Truncated
        if (data.truncated === true) {
            mTruncated.textContent = '⚠️ 잘림';
            mTruncated.className = 'warning';
        } else if (data.truncated === false) {
            mTruncated.textContent = '✅ 정상';
            mTruncated.className = 'success';
        }

        // Score
        if (typeof data.total_score === 'number') {
            mScore.textContent = data.total_score.toFixed(0) + '/100';
            mScore.className = data.total_score >= 80 ? 'success' :
                               data.total_score >= 60 ? 'warning' : 'error';
        }

        // Verify
        if (data.verify_passed === true) {
            mVerify.textContent = '✅ 통과';
            mVerify.className = 'success';
        } else if (data.verify_passed === false) {
            mVerify.textContent = '❌ 실패';
            mVerify.className = 'error';
        }
    }

    function setLoading(loading) {
        startBtn.disabled = loading;
        sendBtn.disabled = loading;
        actionInput.disabled = loading;

        if (loading) {
            sendBtn.innerHTML = '<span class="loading"></span>';
        } else {
            sendBtn.textContent = '전송';
        }
    }

    function showChat() {
        welcomeEl.hidden = true;
        chatEl.hidden = false;
        metricsEl.hidden = false;
    }

    // ===== API 호출 =====

    async function startGame() {
        setLoading(true);
        try {
            const response = await fetch('/game/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({}),
            });

            if (!response.ok) {
                throw new Error('HTTP ' + response.status);
            }

            const data = await response.json();
            sessionId = data.session_id;
            turnNumber = 0;

            sessionStatusEl.textContent = '세션: ' + sessionId.slice(0, 8);
            turnCounterEl.textContent = '턴: ' + turnNumber;

            mLocation.textContent = data.initial_state.location || '-';

            showChat();
            addMessage(
                '게임이 시작되었습니다. ' +
                '작품: ' + (data.plan.work_name || '?') + '. ' +
                '배경: ' + (data.plan.world_setting || '?') + '. ' +
                '시작 위치: ' + (data.initial_state.location || '?') + '.',
                'system'
            );
            actionInput.focus();
        } catch (err) {
            addMessage('게임 시작 실패: ' + err.message, 'error');
        } finally {
            setLoading(false);
        }
    }

    async function sendAction() {
        const action = actionInput.value.trim();
        if (!action || !sessionId) {
            return;
        }

        addMessage(action, 'user');
        actionInput.value = '';
        setLoading(true);

        try {
            const response = await fetch('/game/turn', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: sessionId,
                    user_action: action,
                }),
            });

            if (!response.ok) {
                const errData = await response.json().catch(() => ({}));
                throw new Error(errData.detail || ('HTTP ' + response.status));
            }

            const data = await response.json();
            turnNumber = data.turn_n;

            turnCounterEl.textContent = '턴: ' + turnNumber;

            addMessage(data.response, 'gm');
            updateMetrics(data);

            // 잘림 경고
            if (data.truncated) {
                addMessage('⚠️ 응답이 잘렸을 가능성이 있습니다.', 'system');
            }

            // 위치 업데이트
            await refreshState();
        } catch (err) {
            addMessage('턴 처리 실패: ' + err.message, 'error');
        } finally {
            setLoading(false);
            actionInput.focus();
        }
    }

    async function refreshState() {
        if (!sessionId) {
            return;
        }
        try {
            const response = await fetch('/game/state/' + sessionId);
            if (response.ok) {
                const data = await response.json();
                mLocation.textContent = data.location || '-';
            }
        } catch (err) {
            // 무시 (메인 흐름 차단 X)
        }
    }

    // ===== 이벤트 리스너 =====

    startBtn.addEventListener('click', startGame);
    sendBtn.addEventListener('click', sendAction);

    actionInput.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendAction();
        }
    });
})();
