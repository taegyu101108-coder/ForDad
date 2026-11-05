import csv
import io
import math
from urllib.parse import urlparse

import qrcode
import streamlit as st


def ratio(numerator, denominator, percent=False):
    if numerator is None or denominator is None or denominator <= 0:
        return None
    return numerator / denominator * (100 if percent else 1)


def loan_schedule(principal, annual_rate, months, method):
    """월말 납입, 고정금리, 거치 없음. 금액 단위 백만원, 수수료 제외."""
    if principal < 0 or annual_rate < 0 or months < 1:
        raise ValueError('대출금액·금리는 0 이상, 기간은 1개월 이상이어야 합니다.')
    r = annual_rate / 1200
    payment = principal / months if r == 0 else principal * r / (-math.expm1(-months * math.log1p(r)))
    balance, rows = principal, []
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
    csv.writer(buffer).writerows(rows)
    return buffer.getvalue().encode('utf-8-sig')


def fmt(value, suffix=''):
    return '산출 불가' if value is None else f'{value:,.2f}{suffix}'


def change_text(before, after, unit=''):
    if before is None or after is None:
        return '산출 불가'
    delta = after - before
    return f'{"+" if delta > 0 else ""}{delta:,.2f}{unit}'


def main():
    st.set_page_config(page_title='여신 한눈에', page_icon='🏦', layout='centered')
    st.markdown("""<style>
    :root{color-scheme:dark}
    .stApp,[data-testid="stAppViewContainer"]{background:#0b1220!important;color:#edf3fc!important}
    [data-testid="stHeader"]{background:#0b1220!important;color:#edf3fc!important}
    .block-container{max-width:850px;padding-top:1.3rem;padding-bottom:1.5rem}
    h1,h2,h3,h4,h5,h6{color:#f1f6ff!important}
    [data-testid="stMarkdownContainer"],[data-testid="stMarkdownContainer"] p,
    [data-testid="stMarkdownContainer"] li,[data-testid="stMarkdownContainer"] strong,
    [data-testid="stWidgetLabel"],[data-testid="stWidgetLabel"] p,
    [data-testid="stText"],label{color:#edf3fc!important}
    [data-testid="stCaptionContainer"],[data-testid="stCaptionContainer"] p{color:#bdcce0!important}
    [data-testid="stExpander"]{background:#111d30!important;border:1px solid #34465f!important;border-radius:14px}
    [data-testid="stExpander"] summary{color:#edf3fc!important;background:#152238!important;border-radius:12px}
    [data-testid="stForm"]{background:#111d30!important;border-color:#34465f!important}
    div[data-testid="stMetric"]{background:#16253b!important;border:1px solid #38506d;border-radius:14px;padding:12px}
    [data-testid="stMetricLabel"],[data-testid="stMetricLabel"] p{color:#cbd9eb!important}
    div[data-testid="stMetricValue"]{font-size:1.45rem;color:#ffffff!important}
    input,textarea,[data-baseweb="input"],[data-baseweb="base-input"],[data-baseweb="select"]>div{
    background:#0b1424!important;color:#f4f7ff!important;-webkit-text-fill-color:#f4f7ff!important;border-color:#536b88!important}
    input::placeholder,textarea::placeholder{color:#a8b9d0!important;-webkit-text-fill-color:#a8b9d0!important;opacity:1}
    [data-baseweb="select"] span{color:#f4f7ff!important}
    [data-baseweb="popover"],[data-baseweb="menu"],[role="listbox"],[role="option"]{background:#16253b!important;color:#f4f7ff!important}
    [role="option"]:hover,[role="option"][aria-selected="true"]{background:#2b4564!important}
    [data-testid="stNumberInput"] button{background:#22364f!important;color:#ffffff!important}
    [data-testid="stAlert"]{background:#182d43!important;border:1px solid #54718c!important;color:#f4f7ff!important;border-radius:12px}
    [data-testid="stAlert"] p,[data-testid="stAlert"] strong{color:#f4f7ff!important}
    [data-testid="stDownloadButton"] button,[data-testid="stFormSubmitButton"] button,[data-testid="stButton"] button{
    background:#203a54!important;color:#ffffff!important;border:1px solid #6b89a4!important;border-radius:10px}
    [data-testid="stFormSubmitButton"] button{background:#0d685d!important;border-color:#54c8ad!important}
    button p{color:#ffffff!important}
    .hero{background:linear-gradient(120deg,#143b4c,#125347);color:#ffffff;padding:18px;border:1px solid #397c80;border-radius:18px;margin-bottom:12px}
    .hero small{color:#a8f0d8;letter-spacing:2px}.hero h2{color:#ffffff!important;margin:3px 0;font-size:1.65rem}
    @media(max-width:600px){.block-container{padding-left:12px;padding-right:12px}div[data-testid="stMetricValue"]{font-size:1.15rem}}
    </style>""", unsafe_allow_html=True)
    st.markdown('<div class="hero"><small>CREDIT REVIEW · ASSISTANT</small><h2>🏦 여신 한눈에</h2>숫자는 간결하게, 판단 근거는 명확하게.</div>', unsafe_allow_html=True)
    st.caption('금액 단위: 백만원 · 100백만원 = 1억원 | 연간 재무자료 기준 | 승인·거절 자동 판정 없음')
    if 'result' not in st.session_state:
        st.info('아래 입력을 펼쳐 재무정보를 입력한 뒤 「분석하기」를 눌러주세요.')

    with st.expander('✍️ 기업 재무·대출 입력', expanded='result' not in st.session_state):
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
                    help='원리금 상환에 사용 가능한 현금흐름. 세금·운전자본 증감·필수투자 등을 차감한 뒤 원리금 지급 전 금액을 입력하세요.')
                existing_service = st.number_input('향후 12개월 기존대출 원리금', min_value=0.0, value=None, step=1.0,
                    help='기존 차입의 향후 12개월 원금+이자 합계. 기존 차입이 없다면 0을 입력하세요. 신규대출은 제외합니다.')
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
            if assets is not None and liabilities is not None and liabilities > assets:
                errors.append('총부채가 총자산보다 큽니다. 입력값을 확인하세요.')
            if errors:
                st.session_state.pop('result', None)
                st.error(' / '.join(errors) + ' 입력을 확인하세요.')
            else:
                st.session_state.result = dict(
                    assets=assets, liabilities=liabilities, current_assets=current_assets,
                    current_liabilities=current_liabilities, revenue=revenue,
                    operating_income=operating_income, net_income=net_income, interest=interest,
                    cfads=cfads, existing_service=existing_service, principal=principal,
                    rate=rate, months=months, method=method
                )
                st.rerun()

    d = st.session_state.get('result')
    if d:
        st.caption('아래 결과는 마지막 「분석하기」 제출값 기준입니다. 입력 수정 후 다시 분석하세요.')
        schedule = loan_schedule(d['principal'], d['rate'], d['months'], d['method'])
        first_12 = schedule[:12]
        annual_new = sum(x['납입액(백만원)'] for x in first_12)
        annual_interest_new = sum(x['이자(백만원)'] for x in first_12)
        annual_principal_new = sum(x['원금(백만원)'] for x in first_12)
        total_service_after = None if d['existing_service'] is None else d['existing_service'] + annual_new

        # 가정: 신규 대출금 전액이 현금(유동자산)으로 유입되어 분석 시점에 남아 있음.
        before_equity = None if d['assets'] is None or d['liabilities'] is None else d['assets'] - d['liabilities']
        after_assets = None if d['assets'] is None else d['assets'] + d['principal']
        after_liabilities = None if d['liabilities'] is None else d['liabilities'] + d['principal']
        after_equity = None if after_assets is None or after_liabilities is None else after_assets - after_liabilities
        after_current_assets = None if d['current_assets'] is None else d['current_assets'] + d['principal']
        after_current_liabilities = None if d['current_liabilities'] is None else d['current_liabilities'] + annual_principal_new

        before_interest_coverage = ratio(d['operating_income'], d['interest'])
        after_interest_total = None if d['interest'] is None else d['interest'] + annual_interest_new
        after_interest_coverage = ratio(d['operating_income'], after_interest_total)
        before_dscr = ratio(d['cfads'], d['existing_service'])
        after_dscr = ratio(d['cfads'], total_service_after)

        before_metrics = [
            ('총자산', d['assets'], '백만원'),
            ('총부채', d['liabilities'], '백만원'),
            ('유동비율', ratio(d['current_assets'], d['current_liabilities'], True), '%'),
            ('부채비율', ratio(d['liabilities'], before_equity, True), '%'),
            ('이자보상배율', before_interest_coverage, '배'),
            ('DSCR · 향후 12개월', before_dscr, '배')
        ]
        after_metrics = [
            ('총자산', after_assets, '백만원'),
            ('총부채', after_liabilities, '백만원'),
            ('유동비율', ratio(after_current_assets, after_current_liabilities, True), '%'),
            ('부채비율', ratio(after_liabilities, after_equity, True), '%'),
            ('이자보상배율', after_interest_coverage, '배'),
            ('DSCR · 향후 12개월', after_dscr, '배')
        ]
        metrics = [
            ('유동비율', after_metrics[2][1], '%'),
            ('부채비율', after_metrics[3][1], '%'),
            ('영업이익률', ratio(d['operating_income'], d['revenue'], True), '%'),
            ('이자보상배율', after_interest_coverage, '배'),
            ('DSCR · 향후 12개월', after_dscr, '배'),
            ('순이익률', ratio(d['net_income'], d['revenue'], True), '%')
        ]
        for offset in (0, 3):
            cols = st.columns(3)
            for col, (label, value, unit) in zip(cols, metrics[offset:offset + 3]):
                col.metric(label, fmt(value, unit))
        st.success(f"신규대출 첫 월 납입 **{schedule[0]['납입액(백만원)']:,.2f}백만원** · 첫 12개월 합계 **{annual_new:,.2f}백만원**")

        st.subheader('📊 신규 대출 실행 전후 재무 건전성 비교')
        st.caption('대출금 전액이 현금으로 유입되어 남아 있다고 가정한 추정치입니다. 단위: 백만원.')
        comparison_rows = []
        for before, after in zip(before_metrics, after_metrics):
            label, before_value, unit = before
            after_value = after[1]
            comparison_rows.append({
                '재무 지표': label, '대출 전': fmt(before_value, unit),
                '대출 후': fmt(after_value, unit),
                '변화량': change_text(before_value, after_value, unit)
            })
        st.dataframe(comparison_rows, hide_index=True, use_container_width=True)
        st.markdown('**변화 해석 참고**')
        st.write(f"- 총자산 변화: {change_text(d['assets'], after_assets, '백만원')} / 총부채 변화: {change_text(d['liabilities'], after_liabilities, '백만원')}")
        st.write(f"- 유동비율 변화: {change_text(before_metrics[2][1], after_metrics[2][1], '%')} / 부채비율 변화: {change_text(before_metrics[3][1], after_metrics[3][1], '%')}")
        st.write(f"- 이자보상배율 변화: {change_text(before_interest_coverage, after_interest_coverage, '배')} / DSCR 변화: {change_text(before_dscr, after_dscr, '배')}")
        st.info('비율이 높아지거나 낮아지는 것만으로 자동으로 양호·불량을 판정하지 않습니다. 업종, 자산의 현금화 가능성, 대출금 사용처와 상환 일정을 함께 검토하세요.')

        warnings = []
        if before_equity is not None and before_equity <= 0:
            warnings.append('대출 전 자기자본이 0 이하입니다. 부채비율로 정상 비교할 수 없으며 자본잠식 여부를 별도 검토하세요.')
        if after_equity is not None and after_equity <= 0:
            warnings.append('대출 후 자기자본이 0 이하입니다. 부채비율로 정상 비교할 수 없습니다.')
        if d['operating_income'] is not None and d['operating_income'] < 0:
            warnings.append('영업손실이 입력되었습니다. 지속성 및 현금 유출 원인을 확인하세요.')
        if after_dscr is not None and after_dscr < 1:
            warnings.append('대출 후 DSCR이 1 미만: 입력한 현금흐름이 향후 12개월 원리금 합계보다 작습니다.')
        if d['method'] == '만기일시':
            warnings.append('만기일시 상환: 첫 12개월에 만기가 없으면 DSCR에 만기 원금이 반영되지 않습니다. 만기 자금·차환 가능성을 별도로 검토하세요.')
        if any(v is None for _, v, _ in metrics):
            warnings.append('일부 지표는 입력 누락 또는 분모가 0 이하라 산출하지 않았습니다. 산출 불가가 양호하다는 의미는 아닙니다.')
        for warning in warnings:
            st.warning(warning)

        with st.expander('🔎 계산 근거 · 상환 일정 · 결과 다운로드'):
            st.write('자기자본 = 총자산 − 총부채: ' + fmt(before_equity, '백만원'))
            st.write('대출 후 자기자본 = 대출 후 총자산 − 대출 후 총부채: ' + fmt(after_equity, '백만원'))
            st.write('유동비율 = 유동자산 ÷ 유동부채 × 100 / 부채비율 = 총부채 ÷ 자기자본 × 100')
            st.write('이자보상배율 = 영업이익 ÷ 이자비용 / DSCR = CFADS ÷ 향후 12개월 원리금')
            st.write('대출 전 DSCR = CFADS ÷ 기존 원리금')
            st.write('대출 후 DSCR = CFADS ÷ (기존 원리금 + 신규대출 첫 12개월 원리금)')
            st.write('신규대출 첫 12개월 원금: ' + fmt(annual_principal_new, '백만원'))
            st.write('신규대출 첫 12개월 이자: ' + fmt(annual_interest_new, '백만원'))
            st.write('대출 후 첫 12개월 총 원리금: ' + fmt(total_service_after, '백만원'))
            st.caption('신규대출 즉시 실행·다음 달부터 월말 납입·고정금리·거치 없음 가정. 일수계산·수수료·은행별 반올림은 반영하지 않아 실제 약정과 다를 수 있습니다. 대출 후 이자보상배율은 기존 연이자비용에 신규대출 첫 12개월 이자를 더한 단순 추정치입니다.')
            st.write(f"신규대출 총이자: {sum(x['이자(백만원)'] for x in schedule):,.2f}백만원 · 최대 월 납입: {max(x['납입액(백만원)'] for x in schedule):,.2f}백만원")
            st.dataframe(schedule, hide_index=True, use_container_width=True)

            report = [['여신 한눈에: 검토 보조 / 금액 단위 백만원'], ['입력항목', '값']]
            labels = {
                'assets': '총자산', 'liabilities': '총부채', 'current_assets': '유동자산',
                'current_liabilities': '유동부채', 'revenue': '연매출액',
                'operating_income': '연영업이익', 'net_income': '연당기순이익',
                'interest': '연이자비용', 'cfads': '향후12개월 CFADS',
                'existing_service': '기존12개월원리금', 'principal': '신규대출금',
                'rate': '연금리(%)', 'months': '기간(개월)', 'method': '상환방식'
            }
            report += [[labels[k], v if v is not None else '미입력'] for k, v in d.items()]
            report += [[], ['기본 지표', '대출 후 결과']]
            report += [[label, fmt(value, unit)] for label, value, unit in metrics]
            report += [[], ['재무 지표', '대출 전', '대출 후', '변화량']]
            report += [[r['재무 지표'], r['대출 전'], r['대출 후'], r['변화량']] for r in comparison_rows]
            report += [
                ['대출 전 자기자본', fmt(before_equity, '백만원')],
                ['대출 후 자기자본', fmt(after_equity, '백만원')],
                ['신규 첫12개월 원금', annual_principal_new],
                ['신규 첫12개월 이자', annual_interest_new],
                ['대출 후 첫12개월 원리금', fmt(total_service_after, '백만원')]
            ]
            report += [['주의', w] for w in warnings]
            st.download_button('분석 결과 CSV', csv_bytes(report), 'credit_review.csv', 'text/csv', use_container_width=True)
            st.download_button('상환 일정 CSV', csv_bytes([list(schedule[0].keys())] + [list(x.values()) for x in schedule]), 'repayment_schedule.csv', 'text/csv', use_container_width=True)

    with st.expander('📱 QR 접속 · 사용 및 보안 안내'):
        st.write('GitHub 저장소에 두 파일을 올리고 Streamlit Community Cloud에서 app.py를 배포하세요. 아래에 배포 URL을 넣어 QR을 내려받을 수 있습니다. QR 자체가 앱을 호스팅하지는 않습니다.')
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
        st.caption('QR은 접근통제가 아닙니다. 외부 공개 배포 전 소속 기관 보안 승인을 받으세요. 앱 코드는 입력을 파일·DB에 저장하거나 외부 API로 전송하지 않으나, 호스팅 서버에서 처리되며 별도 인증은 없습니다. 비식별·가상자료로 먼저 검증하세요. 브라우저 새로고침·세션 종료 시 입력이 사라질 수 있습니다.')
        st.caption('업종·회계기준·연결/별도 구분·계절성·담보·보증·연체·차입약정·은행 내부 기준을 별도 확인해야 합니다.')
    st.caption('검토 보조용 · 공식 신용평가 또는 대출 승인/거절 판단이 아닙니다.')


if __name__ == '__main__':
    main()
