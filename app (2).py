"""여신 한눈에 | 실행: streamlit run app.py
GitHub에 app.py와 requirements.txt를 올린 뒤 Streamlit Community Cloud에서 배포하세요.
실제 기업정보를 공개 배포 앱에 입력하기 전 보안·외부 서비스 사용 규정을 확인하세요.
"""
import csv
import io
import math
from urllib.parse import urlparse

import streamlit as st
import qrcode


def ratio(numerator, denominator, percent=False):
    if numerator is None or denominator is None or denominator <= 0:
        return None
    return numerator / denominator * (100 if percent else 1)


def loan_schedule(principal, annual_rate, months, method):
    """월말 납입, 고정금리, 거치 없음. 금액 단위는 백만원. 수수료 제외."""
    if principal < 0 or annual_rate < 0 or months < 1:
        raise ValueError('대출금액·금리는 0 이상, 기간은 1개월 이상이어야 합니다.')
    r = annual_rate / 1200
    payment = principal / months if r == 0 else principal * r / (-math.expm1(-months * math.log1p(r)))
    balance = principal
    rows = []
    for month in range(1, months + 1):
        interest = balance * r
        if method == '원리금균등':
            repayment = min(balance, max(0.0, payment - interest))
        elif method == '원금균등':
            repayment = min(balance, principal / months)
        else:
            repayment = balance if month == months else 0.0
        if month == months:
            repayment = balance
        balance = max(0.0, balance - repayment)
        rows.append({'회차': month, '원금(백만원)': repayment, '이자(백만원)': interest,
                     '납입액(백만원)': repayment + interest, '잔액(백만원)': balance})
    return rows


def csv_bytes(rows):
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerows(rows)
    return buffer.getvalue().encode('utf-8-sig')


def fmt(value, suffix=''):
    return '산출 불가' if value is None else f'{value:,.2f}{suffix}'


def add_styles():
    st.markdown('''<style>
    :root { color-scheme: dark; }
    .stApp,[data-testid="stAppViewContainer"] {background:#0b1220!important;color:#edf3fc!important;}
    [data-testid="stHeader"] {background:#0b1220!important;}
    .block-container {max-width:900px;padding-top:1.5rem;padding-bottom:2rem;}
    h1,h2,h3,h4,h5,h6 {color:#f1f6ff!important;}
    [data-testid="stMarkdownContainer"], [data-testid="stMarkdownContainer"] p,
    [data-testid="stMarkdownContainer"] li, [data-testid="stMarkdownContainer"] strong,
    [data-testid="stWidgetLabel"], [data-testid="stWidgetLabel"] p,
    [data-testid="stText"], label {color:#edf3fc!important;}
    [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p {color:#bdcce0!important;}
    [data-testid="stExpander"] {background:#111d30!important;border:1px solid #34465f!important;border-radius:14px;}
    [data-testid="stExpander"] summary {color:#edf3fc!important;background:#152238!important;border-radius:12px;}
    /* 두 안내/입력 영역은 항상 펼쳐두고 접기 화살표와 접기 동작을 숨김 */
    [data-testid="stExpander"] summary {list-style:none!important;}
    [data-testid="stExpander"] summary svg,
    [data-testid="stExpander"] summary [data-testid="stExpanderToggleIcon"] {display:none!important;}
    [data-testid="stForm"] {background:#111d30!important;border-color:#34465f!important;}
    div[data-testid="stMetric"] {background:#16253b!important;border:1px solid #38506d;border-radius:14px;padding:12px;}
    [data-testid="stMetricLabel"], [data-testid="stMetricLabel"] p {color:#cbd9eb!important;}
    div[data-testid="stMetricValue"] {font-size:1.45rem;color:#ffffff!important;}
    /* 입력칸: 밝은 배경 + 어두운 글씨로 대비를 확실하게 */
    input, textarea, [data-baseweb="input"] input, [data-baseweb="base-input"] input {
      background:#f8fafc!important;color:#172033!important;-webkit-text-fill-color:#172033!important;
      border-color:#9aaec4!important;caret-color:#172033!important;
    }
    input::placeholder, textarea::placeholder {
      color:#64748b!important;-webkit-text-fill-color:#64748b!important;opacity:1!important;
    }
    [data-baseweb="select"]>div {background:#f8fafc!important;color:#172033!important;border-color:#9aaec4!important;}
    [data-baseweb="select"] span {color:#172033!important;-webkit-text-fill-color:#172033!important;}
    [data-baseweb="popover"],[data-baseweb="menu"],[role="listbox"],[role="option"] {background:#f8fafc!important;color:#172033!important;}
    [role="option"] {color:#172033!important;}
    [role="option"]:hover,[role="option"][aria-selected="true"] {background:#dbeafe!important;}
    [data-testid="stNumberInput"] button {background:#22364f!important;color:#ffffff!important;}
    [data-testid="stAlert"] {background:#182d43!important;border:1px solid #54718c!important;color:#f4f7ff!important;border-radius:12px;}
    [data-testid="stAlert"] [data-testid="stMarkdownContainer"], [data-testid="stAlert"] p,
    [data-testid="stAlert"] strong {color:#f4f7ff!important;}
    [data-testid="stDownloadButton"] button,[data-testid="stFormSubmitButton"] button,
    [data-testid="stButton"] button {background:#203a54!important;color:#ffffff!important;
      border:1px solid #6b89a4!important;border-radius:10px;}
    [data-testid="stFormSubmitButton"] button {background:#0d685d!important;border-color:#54c8ad!important;}
    [data-testid="stButton"] button[kind="primary"] {background:#0d806f!important;border-color:#54c8ad!important;}
    button p {color:#ffffff!important;}
    a {color:#83d9f5!important;}
    .hero {background:linear-gradient(120deg,#143b4c,#125347);color:#ffffff;padding:20px;
      border:1px solid #397c80;border-radius:18px;margin-bottom:14px;}
    .hero small {color:#a8f0d8;letter-spacing:2px;}
    .hero h2 {color:#ffffff!important;margin:3px 0;font-size:1.8rem;}
    .intro {background:linear-gradient(145deg,#142b43,#123b43);border:1px solid #3b7180;
      border-radius:22px;padding:30px 28px;margin:8vh auto 0;max-width:760px;}
    .intro h1 {font-size:2.15rem;margin-bottom:8px;}
    .intro-lead {font-size:1.08rem;color:#d6e7f5!important;line-height:1.7;}
    .feature {background:#1a3048;border:1px solid #3a526d;border-radius:13px;padding:14px 16px;margin:10px 0;color:#eaf2fb;}
    .intro-note {font-size:.88rem;color:#bdcce0!important;margin-top:18px;line-height:1.6;}
    @media(max-width:600px) {
      .block-container {padding-left:12px;padding-right:12px;}
      div[data-testid="stMetricValue"] {font-size:1.15rem;}
      .intro {padding:22px 17px;margin-top:3vh;}
      .intro h1 {font-size:1.7rem;}
    }
    </style>''', unsafe_allow_html=True)


def intro_screen():
    st.markdown('''<div class="intro">
      <div style="color:#a8f0d8;letter-spacing:2px;font-size:.82rem;font-weight:700;">FINANCIAL REVIEW TOOL</div>
      <h1>🏦 여신 한눈에</h1>
      <p class="intro-lead">기업의 재무 상태와 신규 대출 실행에 따른 상환 부담을 한 화면에서 살펴보는 재무 분석 보조 프로그램입니다.</p>
      <div class="feature"><b>📊 주요 재무지표 분석</b><br>유동비율, 부채비율, 영업이익률, 이자보상배율, 순이익률 등을 계산합니다.</div>
      <div class="feature"><b>💳 신규 대출 시뮬레이션</b><br>대출금액·금리·기간·상환방식에 따른 월별 상환 일정과 첫 12개월 부담을 계산합니다.</div>
      <div class="feature"><b>📁 결과 저장 및 모바일 접속</b><br>분석 결과와 상환 일정을 CSV로 내려받고, 배포 주소로 QR 코드를 만들 수 있습니다.</div>
      <p class="intro-note">※ 본 프로그램은 검토를 돕는 계산 도구이며 공식 신용평가나 대출 승인·거절 판단을 대신하지 않습니다. 실제 기업정보 대신 비식별 또는 가상자료로 먼저 확인하세요.</p>
    </div>''', unsafe_allow_html=True)
    st.write('')
    _, center, _ = st.columns([1, 2, 1])
    with center:
        if st.button('🚀 시작하기', type='primary', use_container_width=True):
            st.session_state['started'] = True
            st.rerun()


def calculator_screen():
    st.markdown('<div class="hero"><small>CREDIT REVIEW · ASSISTANT</small><h2>🏦 여신 한눈에</h2>숫자는 간결하게, 판단 근거는 명확하게.</div>', unsafe_allow_html=True)
    st.caption('금액 단위: 백만원 · 100백만원 = 1억원 | 연간 재무자료 기준 | 승인·거절 자동 판정 없음')

    with st.container(border=True):  # 항상 표시: 접기/펼치기 화살표 없음
        st.subheader('✍️ 기업 재무·대출 입력')
        st.caption('민감정보 보호를 위해 기업명·사업자번호는 받지 않습니다. 빈칸과 0은 구분됩니다.')
        with st.form('financial_input'):
            c1, c2 = st.columns(2)
            with c1:
                assets = st.number_input('총자산', min_value=0.0, value=None, step=10.0)
                liabilities = st.number_input('총부채', min_value=0.0, value=None, step=10.0)
                current_assets = st.number_input('유동자산', min_value=0.0, value=None, step=10.0)
                current_liabilities = st.number_input('유동부채', min_value=0.0, value=None, step=10.0)
                revenue = st.number_input('연매출액', min_value=0.0, value=None, step=10.0)
            with c2:
                operating_income = st.number_input('연영업이익 (손실은 음수)', value=None, step=1.0)
                net_income = st.number_input('연당기순이익 (손실은 음수)', value=None, step=1.0)
                interest = st.number_input('연이자비용 (해당 재무기간)', min_value=0.0, value=None, step=1.0)
                cfads = st.number_input('향후 12개월 CFADS', value=None, step=1.0,
                    help='원리금 상환에 사용 가능한 현금흐름. 세금·운전자본 증감·필수투자 등 차감 후, 원리금 지급 전 금액을 별도 추정해 입력하세요.')
                existing_service = st.number_input('향후 12개월 기존대출 원리금', min_value=0.0, value=None, step=1.0,
                    help='이미 보유한 모든 차입의 향후 12개월 원금+이자 합계. 기존 차입이 없다면 0을 입력하세요. 아래 신규대출은 제외합니다.')
            st.markdown('**신규 대출 시뮬레이션**')
            a, b = st.columns(2)
            principal = a.number_input('신규 대출금액', min_value=0.0, value=100.0, step=10.0)
            rate = b.number_input('연금리 (%)', min_value=0.0, max_value=100.0, value=5.0, step=0.1)
            months = a.number_input('대출기간 (개월)', min_value=1, max_value=600, value=36, step=1)
            method = b.selectbox('상환방식', ['원리금균등', '원금균등', '만기일시'])
            submitted = st.form_submit_button('분석하기 →', type='primary', use_container_width=True)

        if submitted:
            errors = []
            if assets is not None and current_assets is not None and current_assets > assets:
                errors.append('유동자산이 총자산보다 큽니다.')
            if liabilities is not None and current_liabilities is not None and current_liabilities > liabilities:
                errors.append('유동부채가 총부채보다 큽니다.')
            if errors:
                st.session_state.pop('result', None)
                st.error(' / '.join(errors) + ' 입력을 확인하세요.')
            else:
                st.session_state.result = dict(assets=assets, liabilities=liabilities,
                    current_assets=current_assets, current_liabilities=current_liabilities,
                    revenue=revenue, operating_income=operating_income, net_income=net_income,
                    interest=interest, cfads=cfads, existing_service=existing_service,
                    principal=principal, rate=rate, months=months, method=method)
                st.rerun()

    d = st.session_state.get('result')
    if d:
        st.caption('아래 결과는 마지막 「분석하기」 제출값 기준입니다. 입력 수정 후 다시 분석하세요.')
        equity = None if d['assets'] is None or d['liabilities'] is None else d['assets'] - d['liabilities']
        schedule = loan_schedule(d['principal'], d['rate'], d['months'], d['method'])
        annual_new = sum(row['납입액(백만원)'] for row in schedule[:12])
        total_service = None if d['existing_service'] is None else d['existing_service'] + annual_new
        metrics = [
            ('유동비율', ratio(d['current_assets'], d['current_liabilities'], True), '%'),
            ('부채비율', ratio(d['liabilities'], equity, True), '%'),
            ('영업이익률', ratio(d['operating_income'], d['revenue'], True), '%'),
            ('이자보상배율', ratio(d['operating_income'], d['interest']), '배'),
            ('DSCR · 향후 12개월', ratio(d['cfads'], total_service), '배'),
            ('순이익률', ratio(d['net_income'], d['revenue'], True), '%')]
        for offset in (0, 3):
            columns = st.columns(3)
            for col, (label, value, unit) in zip(columns, metrics[offset:offset + 3]):
                col.metric(label, fmt(value, unit))
        st.success(f"신규대출 첫 월 납입 **{schedule[0]['납입액(백만원)']:,.2f}백만원** · 첫 12개월 합계 **{annual_new:,.2f}백만원**")
        warnings = []
        if equity is not None and equity <= 0:
            warnings.append('자기자본이 0 이하입니다. 부채비율로 정상 비교할 수 없으며 자본잠식 여부를 별도 검토하세요.')
        if d['operating_income'] is not None and d['operating_income'] < 0:
            warnings.append('영업손실이 입력되었습니다. 지속성 및 현금 유출 원인을 확인하세요.')
        dscr = metrics[4][1]
        if dscr is not None and dscr < 1:
            warnings.append('DSCR이 1 미만: 입력한 현금흐름이 향후 12개월 원리금 합계보다 작습니다.')
        if d['method'] == '만기일시':
            warnings.append('만기일시 상환: 첫 12개월에 만기가 없으면 DSCR에 만기 원금이 반영되지 않습니다. 만기 자금·차환 가능성을 별도로 검토하세요.')
        if any(value is None for _, value, _ in metrics):
            warnings.append('일부 지표는 입력 누락 또는 분모가 0 이하라 산출하지 않았습니다. 산출 불가가 양호하다는 의미는 아닙니다.')
        for warning in warnings:
            st.warning(warning)
        with st.expander('🔎 계산 근거 · 상환 일정 · 결과 다운로드', expanded=False):
            st.write('자기자본 = 총자산 − 총부채: ' + fmt(equity, '백만원'))
            st.write('유동비율 = 유동자산 ÷ 유동부채 × 100 / 부채비율 = 총부채 ÷ 자기자본 × 100')
            st.write('영업·순이익률 = 각 이익 ÷ 매출 × 100 / 이자보상배율 = 영업이익 ÷ 해당 기간 이자비용')
            st.write('DSCR = 향후 12개월 CFADS ÷ (기존 원리금 + 신규대출 첫 12개월 원리금)')
            st.write('향후 12개월 총 원리금: ' + fmt(total_service, '백만원'))
            st.caption('신규대출 즉시 실행·다음 달부터 월말 납입·고정금리·거치 없음 가정. 은행별 계산 방식과 실제 약정에 따라 결과는 다를 수 있습니다.')
            st.write(f"신규대출 총이자: {sum(row['이자(백만원)'] for row in schedule):,.2f}백만원 · 최대 월 납입: {max(row['납입액(백만원)'] for row in schedule):,.2f}백만원")
            st.dataframe(schedule, hide_index=True, use_container_width=True)
            report = [['여신 한눈에: 검토 보조 / 금액 단위 백만원'], ['입력항목', '값']]
            labels = {'assets':'총자산','liabilities':'총부채','current_assets':'유동자산','current_liabilities':'유동부채','revenue':'연매출액','operating_income':'연영업이익','net_income':'연당기순이익','interest':'연이자비용','cfads':'향후12개월 CFADS','existing_service':'기존12개월원리금','principal':'신규대출금','rate':'연금리(%)','months':'기간(개월)','method':'상환방식'}
            report += [[labels[key], value if value is not None else '미입력'] for key, value in d.items()]
            report += [[], ['지표', '결과']] + [[label, fmt(value, unit)] for label, value, unit in metrics]
            report += [['자기자본', fmt(equity)], ['신규 첫12개월 원리금', annual_new], ['총12개월 원리금', fmt(total_service)]]
            report += [['주의', warning] for warning in warnings]
            st.download_button('분석 결과 CSV', csv_bytes(report), 'credit_review.csv', 'text/csv', use_container_width=True)
            st.download_button('상환 일정 CSV', csv_bytes([list(schedule[0].keys())] + [list(row.values()) for row in schedule]), 'repayment_schedule.csv', 'text/csv', use_container_width=True)

    with st.container(border=True):  # 항상 표시: 접기/펼치기 화살표 없음
        st.subheader('📱 QR 접속 · 사용 및 보안 안내')
        st.write('GitHub 저장소에 두 파일을 올리고 Streamlit Community Cloud에서 app.py를 배포하세요. 아래에 배포 URL을 넣어 QR을 내려받을 수 있습니다. 휴대폰에서는 QR 촬영 후 링크를 열면 됩니다. QR 자체가 앱을 호스팅하지는 않습니다.')
        url = st.text_input('배포된 앱 URL', placeholder='https://your-app.streamlit.app')
        if url:
            parsed = urlparse(url.strip())
            if parsed.scheme == 'https' and parsed.hostname and not parsed.username and not parsed.password:
                image = qrcode.make(url.strip())
                buffer = io.BytesIO()
                image.save(buffer, format='PNG')
                st.image(buffer.getvalue(), width=180)
                st.download_button('QR 이미지 다운로드', buffer.getvalue(), 'app_qr.png', 'image/png')
            else:
                st.error('인증정보가 없는 올바른 HTTPS 배포 주소를 입력하세요.')
        st.caption('QR은 접근통제가 아닙니다. 앱 코드는 입력을 파일·DB에 저장하거나 외부 API로 전송하지 않지만, 호스팅 서버에서 처리되며 별도 인증은 없습니다. 비식별·가상자료로 먼저 검증하세요. 브라우저 새로고침·세션 종료 시 입력이 사라질 수 있습니다.')
        st.caption('업종·회계기준·연결/별도 구분·계절성·담보·보증·연체·차입약정·은행 내부 기준을 별도 확인해야 합니다.')
    st.caption('검토 보조용 · 공식 신용평가 또는 대출 승인/거절 판단이 아닙니다.')


def main():
    st.set_page_config(page_title='여신 한눈에', page_icon='🏦', layout='centered')
    add_styles()
    if not st.session_state.get('started', False):
        intro_screen()
        return
    calculator_screen()


if __name__ == '__main__':
    main()
