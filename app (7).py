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
    """월말 납입, 고정금리, 거치 없음. 금액 단위는 천만원. 수수료 제외."""
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
        rows.append({'회차': month, '원금(천만원)': repayment, '이자(천만원)': interest,
                     '납입액(천만원)': repayment + interest, '잔액(천만원)': balance})
    return rows


def csv_bytes(rows):
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerows(rows)
    return buffer.getvalue().encode('utf-8-sig')


def fmt(value, suffix=''):
    return '산출 불가' if value is None else f'{value:,.2f}{suffix}'


def add_styles():
    # Streamlit이 선택한 테마(Dark / Light / System)의 CSS 변수를 사용해
    # 배경·글자·입력창 색이 자동으로 함께 바뀌도록 구성합니다.
    st.markdown('''<style>
    :root {
      color-scheme: light dark;
    }
    .stApp, [data-testid="stAppViewContainer"] {
      background: var(--background-color) !important;
      color: var(--text-color) !important;
    }
    [data-testid="stHeader"] {
      background: var(--background-color) !important;
    }
    .block-container {max-width:900px;padding-top:1.5rem;padding-bottom:2rem;}
    h1,h2,h3,h4,h5,h6,
    [data-testid="stMarkdownContainer"],
    [data-testid="stMarkdownContainer"] p,
    [data-testid="stMarkdownContainer"] li,
    [data-testid="stMarkdownContainer"] strong,
    [data-testid="stWidgetLabel"], [data-testid="stWidgetLabel"] p,
    [data-testid="stText"], label {
      color: var(--text-color) !important;
    }
    [data-testid="stCaptionContainer"],
    [data-testid="stCaptionContainer"] p {
      color: var(--text-color) !important;
      opacity: .78;
    }
    [data-testid="stExpander"] {
      background: var(--secondary-background-color) !important;
      border: 1px solid var(--border-color, rgba(128,128,128,.35)) !important;
      border-radius:14px;
    }
    [data-testid="stExpander"] summary {
      color:var(--text-color)!important;
      background:var(--secondary-background-color)!important;
      border-radius:12px;
    }
    [data-testid="stForm"] {
      background:var(--secondary-background-color)!important;
      border-color:var(--border-color, rgba(128,128,128,.35))!important;
    }
    div[data-testid="stMetric"] {
      background:var(--secondary-background-color)!important;
      border:1px solid var(--border-color, rgba(128,128,128,.35));
      border-radius:14px;padding:12px;
    }
    [data-testid="stMetricLabel"], [data-testid="stMetricLabel"] p,
    div[data-testid="stMetricValue"] {
      color:var(--text-color)!important;
    }
    div[data-testid="stMetricValue"] {font-size:1.45rem;}

    /* 입력 위젯은 현재 테마의 색을 따라가며 글자색도 같은 테마 변수로 지정 */
    input, textarea,
    [data-baseweb="input"] input,
    [data-baseweb="base-input"] input {
      background:var(--secondary-background-color)!important;
      color:var(--text-color)!important;
      -webkit-text-fill-color:var(--text-color)!important;
      border-color:var(--border-color, rgba(128,128,128,.5))!important;
      caret-color:var(--text-color)!important;
    }
    input::placeholder, textarea::placeholder {
      color:var(--text-color)!important;
      -webkit-text-fill-color:var(--text-color)!important;
      opacity:.58!important;
    }
    [data-baseweb="select"]>div {
      background:var(--secondary-background-color)!important;
      color:var(--text-color)!important;
      border-color:var(--border-color, rgba(128,128,128,.5))!important;
    }
    [data-baseweb="select"] span {
      color:var(--text-color)!important;
      -webkit-text-fill-color:var(--text-color)!important;
    }
    [data-baseweb="popover"], [data-baseweb="menu"],
    [role="listbox"], [role="option"] {
      background:var(--secondary-background-color)!important;
      color:var(--text-color)!important;
    }
    [role="option"] {color:var(--text-color)!important;}
    [role="option"]:hover, [role="option"][aria-selected="true"] {
      background:var(--primary-color)!important;
      color:white!important;
    }
    [data-testid="stNumberInput"] button {
      background:var(--secondary-background-color)!important;
      color:var(--text-color)!important;
      border-color:var(--border-color, rgba(128,128,128,.5))!important;
    }

    /* 안내창은 테마 배경과 글자색을 함께 사용해 모든 모드에서 대비 유지 */
    [data-testid="stAlert"] {
      background:var(--secondary-background-color)!important;
      border:1px solid var(--border-color, rgba(128,128,128,.4))!important;
      color:var(--text-color)!important;border-radius:12px;
    }
    [data-testid="stAlert"] *, [data-testid="stAlert"] p,
    [data-testid="stAlert"] strong, [data-testid="stAlert"] span {
      color:var(--text-color)!important;
      -webkit-text-fill-color:var(--text-color)!important;
    }
    [data-testid="stDownloadButton"] button,
    [data-testid="stFormSubmitButton"] button,
    [data-testid="stButton"] button {
      background:var(--secondary-background-color)!important;
      color:var(--text-color)!important;
      border:1px solid var(--border-color, rgba(128,128,128,.5))!important;
      border-radius:10px;
    }
    [data-testid="stFormSubmitButton"] button,
    [data-testid="stButton"] button[kind="primary"] {
      background:var(--primary-color)!important;
      color:white!important;
      border-color:var(--primary-color)!important;
    }
    [data-testid="stButton"] button p,
    [data-testid="stFormSubmitButton"] button p {color:inherit!important;}
    a {color:var(--primary-color)!important;}

    /* 브랜드 소개 패널은 세 테마에서 모두 읽히도록 짙은 배경·밝은 글씨 유지 */
    .hero {background:linear-gradient(120deg,#143b4c,#125347);color:#ffffff;padding:20px;
      border:1px solid #397c80;border-radius:18px;margin-bottom:14px;}
    .hero small {color:#a8f0d8;letter-spacing:2px;}
    .hero h2 {color:#ffffff!important;margin:3px 0;font-size:1.8rem;}
    .intro {background:linear-gradient(145deg,#142b43,#123b43);border:1px solid #3b7180;
      border-radius:22px;padding:30px 28px;margin:8vh auto 0;max-width:760px;color:#ffffff;}
    .intro h1 {font-size:2.15rem;margin-bottom:8px;color:#ffffff!important;}
    .intro-lead {font-size:1.08rem;color:#d6e7f5!important;line-height:1.7;}
    .feature {background:#1a3048;border:1px solid #3a526d;border-radius:13px;padding:14px 16px;margin:10px 0;color:#eaf2fb;}
    .feature b {color:#ffffff!important;}
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
      <p class="intro-lead">어려운 회계 용어를 몰라도 사업장의 대출 상환 부담과 재무 상태를 단계별로 살펴볼 수 있는 분석 보조 프로그램입니다.</p>
      <div class="feature"><b>① 간편 대출 진단</b><br>월매출·운영비 등 일상적인 숫자로 대출 전후 월 잔여금을 비교합니다.</div>
      <div class="feature"><b>② 초보자용 상세 분석</b><br>쉬운 설명과 재무제표에서 숫자를 찾는 안내를 보며 주요 재무지표를 계산합니다.</div>
      <div class="feature"><b>③ 전문가용 상세 분석</b><br>재무제표 항목을 직접 입력해 세부 재무비율과 상환 일정을 확인합니다.</div>
      <p class="intro-note">※ 본 프로그램은 검토를 돕는 계산 도구이며 공식 신용평가나 대출 승인·거절 판단을 대신하지 않습니다. 실제 기업정보 대신 비식별 또는 가상자료로 먼저 확인하세요.</p>
    </div>''', unsafe_allow_html=True)
    st.write('')
    _, center, _ = st.columns([1, 2, 1])
    with center:
        if st.button('🚀 시작하기', type='primary', use_container_width=True):
            st.session_state['started'] = True
            st.rerun()


def simple_loan_screen():
    st.subheader('💳 간편 대출 진단')
    st.write('재무제표가 없어도 평소 알고 있는 월별 금액으로 대출 상환 부담을 대략 확인할 수 있습니다.')
    st.info('금액은 모두 **만원** 단위입니다. 예: 5,000만원이면 5000을 입력하세요.')
    with st.form('simple_loan_form'):
        left, right = st.columns(2)
        with left:
            sales = st.number_input('월평균 매출 (만원)', min_value=0.0, value=5000.0, step=100.0)
            costs = st.number_input('월평균 운영비 (만원)', min_value=0.0, value=3500.0, step=100.0,
                help='임대료, 인건비, 재료비, 공과금 등 사업 운영에 드는 월평균 비용입니다.')
            existing = st.number_input('기존 대출 월 상환액 (만원)', min_value=0.0, value=300.0, step=10.0,
                help='현재 갚는 대출의 월 원금과 이자를 합한 금액입니다. 기존 대출이 없다면 0을 입력하세요.')
        with right:
            principal = st.number_input('새로 빌릴 대출금 (만원)', min_value=0.0, value=5000.0, step=100.0)
            rate = st.number_input('예상 연 금리 (%)', min_value=0.0, max_value=100.0, value=5.0, step=0.1)
            months = st.number_input('상환 기간 (개월)', min_value=1, max_value=600, value=60, step=1)
            method = st.selectbox('상환 방식', ['원리금균등', '원금균등', '만기일시'])
        submitted = st.form_submit_button('간편 진단하기 →', type='primary', use_container_width=True)
    if submitted:
        schedule = loan_schedule(principal / 1000, rate, int(months), method)
        new_payment = schedule[0]['납입액(천만원)'] * 1000
        before = sales - costs - existing
        after = before - new_payment
        st.session_state.simple_result = dict(sales=sales, costs=costs, existing=existing,
            principal=principal, rate=rate, months=int(months), method=method,
            new_payment=new_payment, before=before, after=after, schedule=schedule)
    result = st.session_state.get('simple_result')
    if result:
        st.divider()
        st.markdown('### 분석 결과')
        a, b = st.columns(2)
        a.metric('대출 전 월 잔여금', f"{result['before']:,.0f}만원")
        b.metric('대출 후 월 잔여금', f"{result['after']:,.0f}만원",
                 delta=f"{result['after']-result['before']:,.0f}만원")
        st.metric('신규 대출 첫 달 예상 상환액', f"{result['new_payment']:,.0f}만원")
        st.bar_chart({'대출 전 월 잔여금': [result['before']], '대출 후 월 잔여금': [result['after']]})
        if result['after'] < 0:
            st.error('입력한 평균 매출과 운영비 기준으로 신규 대출 실행 후 월 잔여금이 마이너스입니다. 실제 현금흐름과 비용을 다시 확인하세요.')
        elif result['after'] < result['before'] * 0.2:
            st.warning('신규 대출 상환 후 남는 금액이 대출 전보다 크게 줄어듭니다. 매출 변동과 예비자금도 함께 검토하세요.')
        else:
            st.success('입력한 가정에서는 대출 후에도 월 잔여금이 남습니다. 다만 이것만으로 대출 가능 여부나 안전성을 판단할 수는 없습니다.')
        st.caption('월 잔여금 = 월매출 − 월운영비 − 기존 월 상환액 − 신규 대출 월 상환액. 세금, 계절성, 미수금, 재고투자, 예상치 못한 지출 등은 반영하지 않은 단순 추정치입니다.')
        with st.expander('월별 상환 일정 보기'):
            st.dataframe(result['schedule'], hide_index=True, use_container_width=True)
            st.download_button('상환 일정 CSV 다운로드',
                csv_bytes([list(result['schedule'][0].keys())] + [list(row.values()) for row in result['schedule']]),
                'simple_repayment_schedule.csv', 'text/csv')


def detailed_analysis_screen(beginner=True):
    st.subheader('📊 ' + ('초보자용 상세 분석' if beginner else '전문가용 상세 분석'))
    if beginner:
        st.write('각 항목의 쉬운 설명과 재무제표에서 찾는 위치를 확인하면서 입력하세요. 금액 단위는 **천만원**입니다.')
        st.info('예: 20억원은 200, 5억원은 50으로 입력합니다. 재무제표가 없거나 항목을 모르면 간편 대출 진단을 이용하세요.')
        with st.expander('재무제표에서 숫자를 찾는 방법'):
            st.markdown('''
            - **재무상태표**: 총자산, 총부채, 유동자산, 유동부채를 찾습니다.
            - **손익계산서**: 매출액, 영업이익, 당기순이익, 이자비용을 찾습니다.
            - **현금흐름 자료**: CFADS와 향후 12개월 기존 대출 원리금은 별도 추정이 필요할 수 있습니다.
            - 재무제표의 기간과 기준(연결/별도)을 통일하고, 모르는 값은 임의로 추측하지 마세요.
            ''')
    else:
        st.caption('금액 단위: 천만원 · 10천만원 = 1억원 | 연간 재무자료 기준')
    with st.form('financial_input_beginner' if beginner else 'financial_input_expert'):
        st.markdown('**1. 재무상태표에 있는 금액**' if beginner else '**재무상태표 입력**')
        c1, c2 = st.columns(2)
        with c1:
            assets = st.number_input('전체 자산의 합계 · 총자산' if beginner else '총자산 (천만원)', min_value=0.0, value=None, step=1.0,
                help='현금, 예금, 건물, 기계, 재고 등 회사가 가진 자산 전체의 합계입니다. 재무상태표에서 찾으세요.' if beginner else None)
            liabilities = st.number_input('갚아야 할 빚의 합계 · 총부채' if beginner else '총부채 (천만원)', min_value=0.0, value=None, step=1.0,
                help='대출금, 외상매입금 등 회사가 갚아야 할 금액 전체입니다.' if beginner else None)
            current_assets = st.number_input('1년 안에 현금화할 수 있는 자산 · 유동자산' if beginner else '유동자산 (천만원)', min_value=0.0, value=None, step=1.0,
                help='현금·예금·외상매출금·단기 금융상품·재고자산 등이 포함될 수 있습니다.' if beginner else None)
            current_liabilities = st.number_input('1년 안에 갚아야 할 빚 · 유동부채' if beginner else '유동부채 (천만원)', min_value=0.0, value=None, step=1.0,
                help='단기차입금, 외상매입금 등 1년 안에 갚아야 할 부채입니다.' if beginner else None)
        with c2:
            revenue = st.number_input('1년 동안의 매출 합계 · 연매출액' if beginner else '연매출액 (천만원)', min_value=0.0, value=None, step=1.0,
                help='손익계산서의 매출액 항목을 확인하세요.' if beginner else None)
            operating_income = st.number_input('본업으로 벌거나 잃은 금액 · 영업이익' if beginner else '연영업이익 (손실은 음수)', value=None, step=0.1,
                help='매출에서 매출원가와 판매관리비 등을 뺀 금액입니다. 손실이면 음수로 입력하세요.' if beginner else None)
            net_income = st.number_input('세금 등을 반영한 최종 이익 · 당기순이익' if beginner else '연당기순이익 (손실은 음수)', value=None, step=0.1,
                help='손익계산서의 당기순이익(손실)을 확인하세요.' if beginner else None)
            interest = st.number_input('1년 동안 낸 대출 이자 · 이자비용' if beginner else '연이자비용 (천만원)', min_value=0.0, value=None, step=0.1,
                help='해당 재무기간의 이자비용입니다.' if beginner else None)
        st.markdown('**2. 대출 상환에 사용할 현금흐름**' if beginner else '**현금흐름 및 기존 대출**')
        cfads = st.number_input('앞으로 1년 동안 대출 상환에 쓸 수 있는 현금' if beginner else '향후 12개월 CFADS (천만원)', value=None, step=0.1,
            help='세금, 필수 투자, 운전자본 변동 등을 고려한 뒤 대출 원리금을 갚는 데 쓸 수 있는 현금입니다. 모르면 비워 두세요.' if beginner else '원리금 상환에 사용 가능한 현금흐름입니다.')
        existing_service = st.number_input('앞으로 1년 동안 기존 대출의 원금+이자 합계' if beginner else '향후 12개월 기존대출 원리금 (천만원)', min_value=0.0, value=None, step=0.1,
            help='이미 받은 모든 대출의 향후 12개월 원금과 이자 합계입니다. 기존 대출이 없다면 0을 입력하세요.' if beginner else None)
        st.markdown('**3. 새로 받을 대출 조건**')
        a, b = st.columns(2)
        principal = a.number_input('새로 빌릴 금액 (천만원)' if beginner else '신규 대출금액 (천만원)', min_value=0.0, value=10.0, step=1.0)
        rate = b.number_input('예상 연 이자율 (%)' if beginner else '연금리 (%)', min_value=0.0, max_value=100.0, value=5.0, step=0.1)
        months = a.number_input('몇 개월 동안 갚을까요?' if beginner else '대출기간 (개월)', min_value=1, max_value=600, value=36, step=1)
        method = b.selectbox('갚는 방식' if beginner else '상환방식', ['원리금균등', '원금균등', '만기일시'])
        submitted = st.form_submit_button('상세 분석하기 →', type='primary', use_container_width=True)
    if submitted:
        errors = []
        if assets is not None and current_assets is not None and current_assets > assets:
            errors.append('유동자산이 총자산보다 큽니다.')
        if liabilities is not None and current_liabilities is not None and current_liabilities > liabilities:
            errors.append('유동부채가 총부채보다 큽니다.')
        if errors:
            st.error(' / '.join(errors) + ' 입력을 확인하세요.')
        else:
            st.session_state.detailed_result = dict(assets=assets, liabilities=liabilities,
                current_assets=current_assets, current_liabilities=current_liabilities,
                revenue=revenue, operating_income=operating_income, net_income=net_income,
                interest=interest, cfads=cfads, existing_service=existing_service,
                principal=principal, rate=rate, months=int(months), method=method)
    d = st.session_state.get('detailed_result')
    if d:
        show_detailed_results(d)


def show_detailed_results(d):
    st.divider()
    st.markdown('### 분석 결과')
    equity = None if d['assets'] is None or d['liabilities'] is None else d['assets'] - d['liabilities']
    schedule = loan_schedule(d['principal'], d['rate'], d['months'], d['method'])
    annual_new = sum(row['납입액(천만원)'] for row in schedule[:12])
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
    st.success(f"신규대출 첫 월 납입 **{schedule[0]['납입액(천만원)']:,.2f}천만원** · 첫 12개월 합계 **{annual_new:,.2f}천만원**")
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
    with st.expander('🔎 계산 근거 · 상환 일정 · 결과 다운로드'):
        st.write('자기자본 = 총자산 − 총부채: ' + fmt(equity, '천만원'))
        st.write('유동비율 = 유동자산 ÷ 유동부채 × 100 / 부채비율 = 총부채 ÷ 자기자본 × 100')
        st.write('영업·순이익률 = 각 이익 ÷ 매출 × 100 / 이자보상배율 = 영업이익 ÷ 해당 기간 이자비용')
        st.write('DSCR = 향후 12개월 CFADS ÷ (기존 원리금 + 신규대출 첫 12개월 원리금)')
        st.write('향후 12개월 총 원리금: ' + fmt(total_service, '천만원'))
        st.caption('고정금리·거치 없음 가정. 실제 금융기관의 계산 방식과 약정에 따라 결과는 다를 수 있습니다.')
        st.write(f"신규대출 총이자: {sum(row['이자(천만원)'] for row in schedule):,.2f}천만원 · 최대 월 납입: {max(row['납입액(천만원)'] for row in schedule):,.2f}천만원")
        st.dataframe(schedule, hide_index=True, use_container_width=True)
        labels = {'assets':'총자산','liabilities':'총부채','current_assets':'유동자산','current_liabilities':'유동부채','revenue':'연매출액','operating_income':'연영업이익','net_income':'연당기순이익','interest':'연이자비용','cfads':'향후12개월 CFADS','existing_service':'기존12개월원리금','principal':'신규대출금','rate':'연금리(%)','months':'기간(개월)','method':'상환방식'}
        report = [['여신 한눈에: 검토 보조 / 금액 단위 천만원'], ['입력항목', '값']]
        report += [[labels[key], value if value is not None else '미입력'] for key, value in d.items()]
        report += [[], ['지표', '결과']] + [[label, fmt(value, unit)] for label, value, unit in metrics]
        report += [['자기자본', fmt(equity)], ['신규 첫12개월 원리금', annual_new], ['총12개월 원리금', fmt(total_service)]]
        report += [['주의', warning] for warning in warnings]
        st.download_button('분석 결과 CSV', csv_bytes(report), 'credit_review.csv', 'text/csv', use_container_width=True)
        st.download_button('상환 일정 CSV', csv_bytes([list(schedule[0].keys())] + [list(row.values()) for row in schedule]), 'repayment_schedule.csv', 'text/csv', use_container_width=True)


def calculator_screen():
    st.markdown('<div class="hero"><small>CREDIT REVIEW · ASSISTANT</small><h2>🏦 여신 한눈에</h2>사업 상황에 맞는 분석 방식을 선택하세요.</div>', unsafe_allow_html=True)
    mode = st.radio('분석 방식 선택', ['간편 대출 진단', '초보자용 상세 분석', '전문가용 상세 분석'], key='analysis_mode')
    if mode == '간편 대출 진단':
        simple_loan_screen()
    elif mode == '초보자용 상세 분석':
        detailed_analysis_screen(beginner=True)
    else:
        detailed_analysis_screen(beginner=False)

    st.divider()
    with st.container(border=True):
        st.subheader('📱 QR 접속 · 사용 및 보안 안내')
        st.write('배포된 앱 주소를 입력하면 휴대폰으로 접속할 QR 코드를 만들 수 있습니다. QR 자체가 앱을 호스팅하거나 접근을 제한하지는 않습니다.')
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
        st.caption('앱은 입력값을 별도 파일·DB에 저장하거나 외부 API로 전송하지 않도록 구성되어 있습니다. 다만 호스팅 서버에서 입력값이 처리되므로 실제 민감정보 대신 비식별·가상자료로 먼저 검증하세요.')
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
