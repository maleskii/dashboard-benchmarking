import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os
from datetime import datetime
import seaborn as sns
import matplotlib.pyplot as plt
import re

# Configuração da página
st.set_page_config(
    page_title="Benchmarking de Mercado - Dashboard Completo",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS customizado
st.markdown("""
<style>
.main-header {
    font-size: 3rem;
    font-weight: bold;
    color: #1f77b4;
    text-align: center;
    margin-bottom: 2rem;
}
.intro-box {
    background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
    padding: 2rem;
    border-radius: 15px;
    margin: 1rem 0;
    border-left: 5px solid #1f77b4;
}
.feature-card {
    background: white;
    padding: 1.5rem;
    border-radius: 10px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    margin: 1rem 0;
    border-top: 3px solid #1f77b4;
    height: 100%;
}
.metric-card {
    background: #f0f2f6;
    padding: 1.5rem;
    border-radius: 10px;
    border-left: 5px solid #1f77b4;
    text-align: center;
}
.kpi-card {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 1.5rem;
    border-radius: 15px;
    text-align: center;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
}
.kpi-value {
    font-size: 2.5rem;
    font-weight: bold;
    margin: 0.5rem 0;
}
.kpi-label {
    font-size: 1rem;
    opacity: 0.9;
}
</style>
""", unsafe_allow_html=True)


def limpar_nomes_colunas(df):
    """Remove espaços extras dos nomes das colunas"""
    df.columns = df.columns.str.strip()
    return df


def processar_valores_monetarios(df):
    """
    Processa colunas de preços para garantir formato correto
    Lida com formatos brasileiros (1.200,00) e internacionais (1200.00)
    """
    # Primeiro, limpar nomes das colunas
    df = limpar_nomes_colunas(df)

    colunas_preco = ['Initial_Price', 'Final_Price']

    for col in colunas_preco:
        if col in df.columns:
            # Converter para string primeiro para manipular
            df[col] = df[col].astype(str)

            # Remover símbolos de moeda se existirem
            df[col] = df[col].str.replace('R$', '', regex=False)
            df[col] = df[col].str.replace('r$', '', regex=False)
            df[col] = df[col].str.strip()

            # Detectar e converter formato brasileiro (1.200,00)
            # Se tem vírgula E ponto, assumir formato brasileiro
            mask_br = df[col].str.contains(',') & df[col].str.contains('\.')
            df.loc[mask_br, col] = df.loc[mask_br, col].str.replace('.', '', regex=False)
            df.loc[mask_br, col] = df.loc[mask_br, col].str.replace(',', '.', regex=False)

            # Se tem apenas vírgula, converter para ponto
            mask_virgula = df[col].str.contains(',') & ~df[col].str.contains('\.')
            df.loc[mask_virgula, col] = df.loc[mask_virgula, col].str.replace(',', '.', regex=False)

            # Converter para float
            df[col] = pd.to_numeric(df[col], errors='coerce')

            # CORREÇÃO ESPECIAL: Se encontrar valores muito baixos que parecem estar divididos
            # Detectar se há valores entre 0.1 e 10 que deveriam ser multiplicados
            valores_validos = df[col].dropna()
            if len(valores_validos) > 0:
                # Se temos valores menores que 10 e também valores maiores que 100
                tem_valores_pequenos = (valores_validos < 10).any()
                tem_valores_grandes = (valores_validos > 100).any()

                if tem_valores_pequenos and tem_valores_grandes:
                    # Provavelmente alguns valores estão divididos
                    # Multiplicar apenas valores menores que 10
                    df.loc[df[col] < 10, col] = df.loc[df[col] < 10, col] * 1000
                elif valores_validos.max() < 10:
                    # Se TODOS os valores são menores que 10, multiplicar todos
                    df[col] = df[col] * 1000

    return df


# Função para carregar dados padrão
@st.cache_data
def load_default_data():
    """Carrega os dados padrão do arquivo local"""
    # Removida a funcionalidade de carregar dados padrão
    return None


# Função para categorizar faixa de preço
def categorizar_faixa_preco(preco):
    """Categoriza o preço em faixas de 50 em 50"""
    faixas = [
        (0, 50), (50, 100), (100, 150), (150, 200), (200, 250),
        (250, 300), (300, 350), (350, 400), (400, 450), (450, 500),
        (500, 550), (550, 600), (600, 650), (650, 700), (700, 750),
        (750, 800), (800, 850), (850, 900), (900, 950), (950, 1000)
    ]
    try:
        preco = float(preco)
        for low, high in faixas:
            if low <= preco < high:
                return f"{low}-{high}"
        if preco >= 1000:
            return "1000+"
    except:
        return "0-50"


# Função para formatar valor em reais no padrão brasileiro
def formatar_reais(valor):
    try:
        return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return valor


# Inicializar session state para dados
if 'df' not in st.session_state:
    st.session_state.df = load_default_data()

# Título principal
st.markdown('<h1 class="main-header"> 📊 Benchmarking de Mercado</h1>', unsafe_allow_html=True)

# Criar as abas (reordenadas com a nova aba)
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📘 Bem Vindo",
    "🏢 Dashboard por Marca",
    "📊 Posicionamento de Marcas",
    "🎨 Análise de Cores",
    "✨ Lançamentos vs Produtos Antigos"
])

# TAB 1: VISÃO GERAL E UPLOAD
with tab1:
    st.markdown("""
    <div class="intro-box">
    <h2>Painel de Benchmarking</h2>
    <p>
    Essa ferramenta integra o poder do <strong>webscraping automatizado</strong> com a <strong>análise comparativa (benchmarking)</strong>, reunindo dados atualizados de produtos dos principais concorrentes, tudo em um painel interativo, prático e visual.
    </p>
    <h4>Como Funciona?</h4>
    <ul>
        <li><strong>Coleta Automática de Dados:</strong> Coletamos de forma eficiente, informações relevantes do mercado, como preços, cores e categorias de produtos.</li>
        <li><strong>Análise e Benchmarking:</strong> Tratamos os dados coletados, apresentando comparativos e indicadores estratégicos para apoiar a sua tomada de decisão.</li>
        <li><strong>Visualização Intuitiva:</strong> Acesse gráficos, tabelas e relatórios claros, permitindo identificar rapidamente oportunidades e pontos de melhoria.</li>
    </ul>
    <h4>Principais Benefícios</h4>
    <ul>
        <li>Decisões baseadas em dados reais e atualizados</li>
        <li>Economia de tempo com coleta automatizada</li>
        <li>Visão estratégica do mercado e da concorrência</li>
    </ul>

    </div>
    """, unsafe_allow_html=True)

    st.markdown("## 📌 Análises Disponíveis")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        <div class="feature-card">
        <h4>🏢 Dashboard por Marca</h4>
        <p><strong>O que analisa:</strong> Visão completa e detalhada de uma marca específica, incluindo KPIs, mix de produtos e análises de preço.</p>
        <p><strong>Insights possíveis:</strong></p>
        <ul>
        <li>Performance geral da marca</li>
        <li>Estratégia de precificação</li>
        <li>Composição do portfólio</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="feature-card">
        <h4>🎨 Análise de Cores</h4>
        <p><strong>O que analisa:</strong> Distribuição de cores dos produtos por categoria, mostrando as tendências cromáticas do setor.</p>
        <p><strong>Insights possíveis:</strong></p>
        <ul>
        <li>Tendências de cores por marca</li>
        <li>Diversidade cromática</li>
        <li>Cores mais populares</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="feature-card">
        <h4>📊 Posicionamento de Marcas</h4>
        <p><strong>O que analisa:</strong> Comparativo visual entre diferentes marcas do mercado, mostrando como se distribuem nas categorias e faixas de preço.</p>
        <p><strong>Insights possíveis:</strong></p>
        <ul>
        <li>Identificar gaps de mercado</li>
        <li>Comparar estratégias de pricing</li>
        <li>Analisar diversidade de portfólio</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="feature-card">
        <h4>✨ Ciclo de Produtos</h4>
        <p><strong>O que analisa:</strong> Proporção entre lançamentos (New In) e produtos antigos, indicando a velocidade de renovação do portfólio.</p>
        <p><strong>Insights possíveis:</strong></p>
        <ul>
        <li>Taxa de inovação</li>
        <li>Estratégia de lançamentos</li>
        <li>Ciclo de vida dos produtos</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    with st.expander("⚙️ Configurações de Dados", expanded=False):
        st.markdown("### 📁 Carregar Dados Personalizados")

        uploaded_file = st.file_uploader(
            "Escolha um arquivo CSV ou Excel",
            type=["csv", "xlsx"],
            help="""O arquivo deve conter as colunas:
            - Brand (marca)
            - Product_Category (categoria do produto)
            - Initial_Price e Final_Price (preços)
            - Cor_Categorizada ou Color (cores)
            - Is_Launch (se é lançamento)
            - Name (nome do produto)"""
        )

        if uploaded_file is not None:
            try:
                if uploaded_file.name.endswith(".csv"):
                    df_temp = pd.read_csv(uploaded_file)
                else:
                    df_temp = pd.read_excel(uploaded_file)

                # Processar valores monetários
                df_temp = processar_valores_monetarios(df_temp)

                # Verificar colunas necessárias
                required_cols = ['Brand', 'Product_Category', 'Initial_Price', 'Final_Price']
                if all(col in df_temp.columns for col in required_cols):
                    st.session_state.df = df_temp
                    st.success("✅ Arquivo carregado com sucesso!")
                    st.info(f"📊 Total de registros: {len(df_temp):,}")
                else:
                    st.error("❌ O arquivo não contém todas as colunas necessárias")
                    st.info("Colunas necessárias: " + ", ".join(required_cols))
                    st.warning("Colunas encontradas: " + ", ".join(df_temp.columns.tolist()))
            except Exception as e:
                st.error(f"❌ Erro ao carregar arquivo: {str(e)}")

    # Métricas gerais (se houver dados)
    if st.session_state.df is not None:
        st.markdown("---")
        st.markdown("### 📊 Métricas Gerais do Dataset")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            total_produtos = len(st.session_state.df)
            st.metric("Total de Produtos", f"{total_produtos:,}")

        with col2:
            marcas_unicas = st.session_state.df['Brand'].nunique()
            st.metric("Marcas", marcas_unicas)

        with col3:
            categorias_unicas = st.session_state.df['Product_Category'].nunique()
            st.metric("Categorias", categorias_unicas)

        with col4:
            preco_medio = st.session_state.df['Initial_Price'].mean()
            st.metric("Preço Médio", f"R$ {preco_medio:.2f}")

# TAB 2: DASHBOARD POR MARCA (NOVA)
with tab2:
    st.subheader("🏢 Dashboard Completo por Marca")
    st.caption("Análise detalhada e individual de cada marca")

    if st.session_state.df is None:
        st.error("❌ Nenhum dado disponível. Por favor, carregue um arquivo na aba 'Bem Vindo'.")
        st.stop()

    df = st.session_state.df.copy()

    # Filtros principais
    col1, col2, col3 = st.columns([2, 2, 1])

    with col1:
        marca_dashboard = st.selectbox(
            "🏷️ Selecione a Marca",
            options=sorted(df['Brand'].dropna().unique().tolist()),
            key="marca_dashboard"
        )

    with col2:
        tipo_preco_dashboard = st.radio(
            "💰 Tipo de Preço",
            ["Initial_Price", "Final_Price"],
            format_func=lambda x: "Preço Inicial" if x == "Initial_Price" else "Preço Final",
            horizontal=True,
            key="tipo_preco_dashboard"
        )

    # Filtrar dados da marca
    df_marca = df[df['Brand'] == marca_dashboard].copy()

    # Calcular métricas
    total_produtos_marca = len(df_marca)
    preco_medio_marca = df_marca[tipo_preco_dashboard].mean()
    preco_min_marca = df_marca[tipo_preco_dashboard].min()
    preco_max_marca = df_marca[tipo_preco_dashboard].max()
    amplitude_preco = preco_max_marca - preco_min_marca

    # Calcular taxa de desconto média
    df_marca['desconto_percentual'] = (
                (df_marca['Initial_Price'] - df_marca['Final_Price']) / df_marca['Initial_Price'] * 100)
    desconto_medio = df_marca['desconto_percentual'].mean()

    # KPIs principais
    st.markdown("### 📊 KPIs Principais")
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.markdown(f"""
        <div class="kpi-card" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
            <div class="kpi-label">Total de Produtos</div>
            <div class="kpi-value">{total_produtos_marca}</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="kpi-card" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
            <div class="kpi-label">Preço Médio</div>
            <div class="kpi-value">{formatar_reais(preco_medio_marca)}</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="kpi-card" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);">
            <div class="kpi-label">Preço Mínimo</div>
            <div class="kpi-value">{formatar_reais(preco_min_marca)}</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class="kpi-card" style="background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);">
            <div class="kpi-label">Preço Máximo</div>
            <div class="kpi-value">{formatar_reais(preco_max_marca)}</div>
        </div>
        """, unsafe_allow_html=True)

    with col5:
        st.markdown(f"""
        <div class="kpi-card" style="background: linear-gradient(135deg, #30cfd0 0%, #330867 100%);">
            <div class="kpi-label">Desconto Médio</div>
            <div class="kpi-value">{desconto_medio:.1f}%</div>
        </div>
        """, unsafe_allow_html=True)

    # Divisor
    st.markdown("---")

    # Layout em duas colunas
    col_esq, col_dir = st.columns([5, 3])

    with col_esq:
        # Mix de produtos
        st.markdown("### 🎯 Mix de Produtos")

        # Calcular proporções
        mix_produtos = df_marca['Product_Category'].value_counts()
        mix_percentual = (mix_produtos / total_produtos_marca * 100).round(1)

        # Criar DataFrame para melhor visualização
        df_mix = pd.DataFrame({
            'Categoria': mix_produtos.index,
            'Quantidade': mix_produtos.values,
            'Percentual': mix_percentual.values
        })

        # Gráfico de donut
        fig_donut = px.pie(
            df_mix,
            values='Quantidade',
            names='Categoria',
            title=f"Distribuição de Produtos por Categoria - {marca_dashboard}",
            hole=0.4
        )

        fig_donut.update_traces(
            textposition='inside',
            textinfo='percent+label',
            hovertemplate='<b>%{label}</b><br>' +
                          'Quantidade: %{value}<br>' +
                          'Percentual: %{percent}<br>' +
                          '<extra></extra>'
        )

        fig_donut.update_layout(height=400)
        st.plotly_chart(fig_donut, use_container_width=True)

        # Análise de preços por categoria
        st.markdown("### 💰 Análise de Preços por Categoria")

        # Criar box plot
        fig_box = px.box(
            df_marca,
            x='Product_Category',
            y=tipo_preco_dashboard,
            title=f"Distribuição de Preços por Categoria - {marca_dashboard}",
            color='Product_Category'
        )

        fig_box.update_layout(
            xaxis_title="Categoria",
            yaxis_title="Preço (R$)",
            showlegend=False,
            height=400,
            xaxis_tickangle=-45
        )

        st.plotly_chart(fig_box, use_container_width=True)

    with col_dir:
        # Tabela de preços por categoria
        st.markdown("### 📊 Resumo de Preços")

        resumo_precos = df_marca.groupby('Product_Category')[tipo_preco_dashboard].agg(
            ['min', 'mean', 'max', 'count']).round(2)
        resumo_precos.columns = ['Mínimo', 'Média', 'Máximo', 'Qtd']
        resumo_precos = resumo_precos.sort_values('Qtd', ascending=False)

        # Formatar valores
        for col in ['Mínimo', 'Média', 'Máximo']:
            resumo_precos[col] = resumo_precos[col].apply(formatar_reais)

        st.dataframe(
            resumo_precos,
            use_container_width=True,
            height=400
        )

        # Top cores da marca
        if 'Cor_Categorizada' in df_marca.columns:
            st.markdown("### 🎨 Top 5 Cores")

            cores_marca = df_marca['Cor_Categorizada'].value_counts().head(5)

            fig_cores_marca = px.bar(
                x=cores_marca.values,
                y=cores_marca.index,
                orientation='h',
                labels={'x': 'Quantidade', 'y': 'Cor'},
                color=cores_marca.values,
                color_continuous_scale='Viridis'
            )

            fig_cores_marca.update_layout(
                showlegend=False,
                height=300,
                yaxis={'categoryorder': 'total ascending'}
            )

            st.plotly_chart(fig_cores_marca, use_container_width=True)

    # Análise de lançamentos da marca
    if 'Is_Launch' in df_marca.columns:
        st.markdown("---")
        st.markdown("### 🚀 Performance de Lançamentos")

        col1, col2, col3 = st.columns(3)

        # Normalizar coluna Is_Launch
        df_marca['Is_Launch'] = df_marca['Is_Launch'].astype(str).str.strip().str.lower()
        df_marca['Is_Launch'] = df_marca['Is_Launch'].map({
            'true': True, 'sim': True, 'yes': True, '1': True,
            'false': False, 'não': False, 'nao': False, 'no': False, '0': False
        }).fillna(False)

        # Métricas de lançamento
        total_lancamentos = df_marca['Is_Launch'].sum()
        percentual_lancamentos = (total_lancamentos / total_produtos_marca * 100)

        # Preço médio: lançamentos vs produtos antigos
        preco_medio_lancamentos = df_marca[df_marca['Is_Launch'] == True][tipo_preco_dashboard].mean()
        preco_medio_antigos = df_marca[df_marca['Is_Launch'] == False][tipo_preco_dashboard].mean()

        with col1:
            st.metric(
                "Total de Lançamentos",
                f"{total_lancamentos}",
                f"{percentual_lancamentos:.1f}% do portfólio"
            )

        with col2:
            st.metric(
                "Preço Médio - Lançamentos",
                formatar_reais(preco_medio_lancamentos),
                f"{((preco_medio_lancamentos - preco_medio_antigos) / preco_medio_antigos * 100):.1f}% vs antigos"
            )

        with col3:
            st.metric(
                "Preço Médio - Produtos Antigos",
                formatar_reais(preco_medio_antigos)
            )

    # Heatmap de descontos por categoria
    st.markdown("---")
    st.markdown("### 🔥 Heatmap de Descontos por Categoria")

    # Calcular desconto médio por categoria
    df_marca['desconto_percentual'] = (
                (df_marca['Initial_Price'] - df_marca['Final_Price']) / df_marca['Initial_Price'] * 100)
    desconto_categoria = df_marca.groupby('Product_Category')['desconto_percentual'].mean().round(1)

    # Criar visualização
    fig_heatmap_desc = go.Figure(data=go.Heatmap(
        z=[desconto_categoria.values],
        x=desconto_categoria.index,
        y=['Desconto %'],
        colorscale='RdYlGn',
        text=[[f"{val:.1f}%" for val in desconto_categoria.values]],
        texttemplate="%{text}",
        textfont={"size": 14},
        hoverongaps=False
    ))

    fig_heatmap_desc.update_layout(
        height=200,
        xaxis_title="Categoria",
        yaxis_title=""
    )

    st.plotly_chart(fig_heatmap_desc, use_container_width=True)

# TAB 3: POSICIONAMENTO DE MARCAS (antiga TAB 2)
with tab3:
    st.subheader("📊 Análise Comparativa de Posicionamento")

    if st.session_state.df is None:
        st.error("❌ Nenhum dado disponível. Por favor, carregue um arquivo na aba 'Bem Vindo'.")
        st.stop()

    df = st.session_state.df.copy()

    # Garante que os preços estejam como float para evitar erros de formatação
    df['Initial_Price'] = pd.to_numeric(df['Initial_Price'], errors='coerce')
    df['Final_Price'] = pd.to_numeric(df['Final_Price'], errors='coerce')

    # Filtros
    col1, col2, col3 = st.columns(3)

    with col1:
        marcas = sorted(df['Brand'].dropna().unique().tolist())
        if len(marcas) < 2:
            st.error("É necessário ao menos duas marcas nos dados.")
            st.stop()
        marca1 = st.selectbox("🏷️ Marca 1", options=marcas, index=0)

    with col2:
        outras_marcas = [m for m in marcas if m != marca1]
        marca2 = st.selectbox("🏷️ Marca 2", options=outras_marcas, index=0)

    with col3:
        tipo_preco = st.radio(
            "💰 Tipo de Preço",
            ["Initial_Price", "Final_Price"],
            format_func=lambda x: "Preço Inicial" if x == "Initial_Price" else "Preço Final"
        )

    # Processar dados
    df_filtered = df[df['Brand'].isin([marca1, marca2])].copy()
    df_filtered['Faixa_Preco'] = df_filtered[tipo_preco].apply(categorizar_faixa_preco)

    df_grouped = df_filtered.groupby(['Faixa_Preco', 'Product_Category', 'Brand']).size().reset_index(
        name='Contagem')

    # Ordenar faixas
    ordem_faixas = [
        "0-50", "50-100", "100-150", "150-200", "200-250", "250-300", "300-350", "350-400", "400-450", "450-500",
        "500-550", "550-600", "600-650", "650-700", "700-750", "750-800", "800-850", "850-900", "900-950", "950-1000",
        "1000+"
    ]
    df_grouped['Faixa_Preco'] = pd.Categorical(df_grouped['Faixa_Preco'], categories=ordem_faixas, ordered=True)
    df_grouped['Product_Category'] = pd.Categorical(
        df_grouped['Product_Category'],
        ordered=True,
        categories=sorted(df_grouped['Product_Category'].unique(), reverse=True)
    )

    # Criar gráfico
    fig = px.scatter(
        df_grouped,
        x='Faixa_Preco',
        y='Product_Category',
        size='Contagem',
        color='Brand',
        color_discrete_map={marca1: '#FF6B6B', marca2: '#4ECDC4'},
        labels={
            'Faixa_Preco': 'Faixa de Preço (R$)',
            'Product_Category': 'Categoria',
            'Contagem': 'Nº de Produtos'
        },
        title=f"Comparativo entre {marca1} e {marca2}: Categorias vs Faixas de Preço",
        height=700,
        opacity=0.7
    )

    fig.update_traces(
        mode='markers',
        marker=dict(
            sizemode='area',
            sizeref=2. * max(df_grouped['Contagem']) / (100. ** 2),
            line_width=2
        )
    )

    fig.update_layout(
        xaxis=dict(
            type='category',
            categoryorder='array',
            categoryarray=ordem_faixas,
            tickangle=-45
        ),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(size=12)
    )

    st.plotly_chart(fig, use_container_width=True)

    # 📊 Métricas Comparativas por Categoria
    st.markdown("### 📊 Métricas Comparativas por Categoria")


    # Função auxiliar para calcular métricas por categoria para uma marca
    def calcular_metrica_por_categoria(df, marca, tipo_preco):
        df_marca = df[df['Brand'] == marca]
        resumo = df_marca.groupby('Product_Category')[tipo_preco].agg(['min', 'mean', 'max']).reset_index()
        resumo.columns = ['Categoria', 'Preço Mínimo', 'Preço Médio', 'Preço Máximo']
        return resumo


    # Gerar resumo para ambas as marcas
    resumo_marca1 = calcular_metrica_por_categoria(df_filtered, marca1, tipo_preco)
    resumo_marca2 = calcular_metrica_por_categoria(df_filtered, marca2, tipo_preco)

    # Mesclar os dois resumos lado a lado por categoria
    resumo_comparativo = pd.merge(
        resumo_marca1,
        resumo_marca2,
        on='Categoria',
        how='outer',
        suffixes=(f' - {marca1}', f' - {marca2}')
    ).sort_values('Categoria')

    # Exibir como tabela no Streamlit, formatando os preços certinho
    st.dataframe(resumo_comparativo.style.format({
        f'Preço Mínimo - {marca1}': formatar_reais,
        f'Preço Médio - {marca1}': formatar_reais,
        f'Preço Máximo - {marca1}': formatar_reais,
        f'Preço Mínimo - {marca2}': formatar_reais,
        f'Preço Médio - {marca2}': formatar_reais,
        f'Preço Máximo - {marca2}': formatar_reais,
    }), use_container_width=True)

    st.markdown("### 🌍 Visão Geral: Preço Médio por Categoria - Todas as Marcas")

    # Filtro para tipo de preço
    tipo_preco_geral = st.radio(
        "💰 Escolha o tipo de preço:",
        ["Initial_Price", "Final_Price"],
        index=0,
        horizontal=True,
        format_func=lambda x: "Preço de Lançamento" if x == "Initial_Price" else "Preço Final",
        key="heatmap_geral_preco"
    )

    # Agrupar e pivotar os dados para todas as marcas
    df_geral = df.copy()
    heatmap_geral = df_geral.groupby(['Product_Category', 'Brand'])[tipo_preco_geral].mean().unstack()

    # Ordenar visualmente
    heatmap_geral = heatmap_geral.sort_index().sort_index(axis=1)

    # Criar o heatmap
    fig2, ax2 = plt.subplots(figsize=(14, 6))

    sns.heatmap(
        heatmap_geral,
        annot=True,
        fmt=".2f",
        cmap="YlGnBu",
        linewidths=0.5,
        linecolor='white',
        cbar_kws={'label': 'Preço Médio (R$)'}
    )

    ax2.set_title("💡 Média de Preço por Categoria e Marca (Visão Geral)", fontsize=10, pad=20)
    ax2.set_xlabel("Marca", fontsize=10)
    ax2.set_ylabel("Categoria", fontsize=10)

    plt.xticks(rotation=45, ha='right')
    plt.yticks(rotation=0)

    st.pyplot(fig2)

# TAB 4: ANÁLISE DE CORES (antiga TAB 3)
with tab4:
    st.subheader("🎨 Análise da Variação de Cores")
    st.caption("Analisa quantas variações de cores existem por produto e a distribuição geral de cores")

    if st.session_state.df is None:
        st.error("❌ Nenhum dado disponível. Por favor, carregue um arquivo na aba 'Bem Vindo'.")
        st.stop()

    df = st.session_state.df

    # Verificar se existe a coluna Cor_Categorizada
    if 'Cor_Categorizada' not in df.columns:
        st.warning("⚠️ A coluna 'Cor_Categorizada' não foi encontrada nos dados.")
        st.info("Esta análise requer a coluna 'Cor_Categorizada' no arquivo de dados.")
        st.stop()

    if 'Name' not in df.columns:
        st.warning("⚠️ A coluna 'Name' (nome do produto) não foi encontrada nos dados.")
        st.stop()

    cor_column = 'Cor_Categorizada'

    # Filtro de marca
    marca_selecionada = st.selectbox(
        "🏷️ Selecione a Marca",
        options=['Todas'] + sorted(df['Brand'].dropna().unique().tolist())
    )

    # Filtrar dados
    if marca_selecionada != 'Todas':
        df_cores = df[df['Brand'] == marca_selecionada].copy()
    else:
        df_cores = df.copy()

    # Análise 1: Top 10 cores mais utilizadas
    st.markdown("### 🎨 Top 10 Cores Mais Utilizadas")

    cores_count = df_cores[cor_column].value_counts().head(10)

    fig_cores = px.bar(
        x=cores_count.values,
        y=cores_count.index,
        orientation='h',
        labels={'x': 'Quantidade', 'y': 'Cor'},
        title=f"Cores Mais Utilizadas - {marca_selecionada}",
        color=cores_count.values,
        color_continuous_scale='Viridis'
    )

    fig_cores.update_layout(
        height=500,
        showlegend=False,
        yaxis={'categoryorder': 'total ascending'}
    )

    st.plotly_chart(fig_cores, use_container_width=True)

    # Análise 2: Distribuição de cores por categoria
    st.markdown("### 📊 Distribuição de Cores por Categoria")

    # Criar matriz de cores por categoria usando Cor_Categorizada
    cores_categoria = df_cores.groupby(['Product_Category', cor_column]).size().reset_index(name='Quantidade')

    # Pegar top 5 categorias e top 10 cores para melhor visualização
    top_categorias = df_cores['Product_Category'].value_counts().head(5).index
    top_cores = df_cores[cor_column].value_counts().head(10).index

    cores_categoria_filtered = cores_categoria[
        (cores_categoria['Product_Category'].isin(top_categorias)) &
        (cores_categoria[cor_column].isin(top_cores))
        ]

    if not cores_categoria_filtered.empty:
        matriz_cores = cores_categoria_filtered.pivot(
            index='Product_Category',
            columns=cor_column,
            values='Quantidade'
        ).fillna(0)

        fig_heatmap = px.imshow(
            matriz_cores,
            labels=dict(x="Cor", y="Categoria", color="Quantidade"),
            title=f"Mapa de Calor: Cores por Categoria - {marca_selecionada}",
            color_continuous_scale='Blues',
            aspect='auto'
        )

        fig_heatmap.update_layout(height=500)
        st.plotly_chart(fig_heatmap, use_container_width=True)

        # Análise 3: Distribuição percentual de cores (Gráfico de Pizza)
        st.markdown("### 🥧 Distribuição Percentual de Cores")

        # Contar todas as cores e calcular percentuais
        cores_totais = df_cores[cor_column].value_counts()

        # Pegar top 15 cores para o gráfico de pizza (para não ficar muito poluído)
        top_cores_pizza = cores_totais.head(15)

        # Se houver mais de 15 cores, agrupar o resto como "Outras"
        if len(cores_totais) > 15:
            outras_cores = cores_totais[15:].sum()
            top_cores_pizza = pd.concat([top_cores_pizza, pd.Series({'Outras': outras_cores})])

        fig_pizza_cores = px.pie(
            values=top_cores_pizza.values,
            names=top_cores_pizza.index,
            title=f"Distribuição Percentual das Cores - {marca_selecionada}",
            hole=0.3  # Cria um donut chart
        )

        fig_pizza_cores.update_traces(
            textposition='inside',
            textinfo='percent+label',
            hovertemplate='<b>%{label}</b><br>' +
                          'Quantidade: %{value}<br>' +
                          'Percentual: %{percent}<br>' +
                          '<extra></extra>'
        )

        fig_pizza_cores.update_layout(
            height=500,
            showlegend=True,
            legend=dict(
                orientation="v",
                yanchor="middle",
                y=0.5,
                xanchor="left",
                x=1.05
            )
        )

        st.plotly_chart(fig_pizza_cores, use_container_width=True)

        # Métricas de cores
        col1, col2, col3 = st.columns(3)

        with col1:
            total_cores = df_cores[cor_column].nunique()
            st.metric("🎨 Total de Cores", total_cores)

        with col2:
            media_cores_produto = df_cores.groupby('Name')[cor_column].nunique().mean()
            st.metric("📊 Média de Cores/Produto", f"{media_cores_produto:.1f}")

        with col3:
            cor_mais_comum = df_cores[cor_column].mode()[0] if not df_cores[cor_column].mode().empty else "N/A"
            st.metric("🏆 Cor Mais Comum", cor_mais_comum)

# TAB 5: LANÇAMENTOS VS PRODUTOS ANTIGOS (antiga TAB 4)
with tab5:
    st.subheader("✨ Análise de Lançamentos vs Produtos Antigos")

    if st.session_state.df is None:
        st.error("❌ Nenhum dado disponível. Por favor, carregue um arquivo na aba 'Bem Vindo'.")
        st.stop()

    df = st.session_state.df

    # Verificar presença da coluna 'Is_Launch'
    if 'Is_Launch' not in df.columns:
        st.warning("⚠️ A coluna 'Is_Launch' não foi encontrada nos dados.")
        st.info("Esta análise requer a coluna 'Is_Launch' no arquivo.")
        st.stop()

    # Normalização robusta da coluna Is_Launch
    df['Is_Launch'] = df['Is_Launch'].astype(str).str.strip().str.lower()
    df['Is_Launch'] = df['Is_Launch'].map({
        'true': True, 'sim': True, 'yes': True, '1': True,
        'false': False, 'não': False, 'nao': False, 'no': False, '0': False
    })
    df['Is_Launch'] = df['Is_Launch'].fillna(False)

    # Filtro de marca
    col1, col2 = st.columns([2, 3])
    with col1:
        marca_lancamento = st.selectbox(
            "🏷️ Selecione a Marca",
            options=['Todas'] + sorted(df['Brand'].dropna().unique().tolist()),
            key="marca_lancamento"
        )

    # Filtrar dados pela marca selecionada
    df_launch = df.copy()
    if marca_lancamento != 'Todas':
        df_launch = df_launch[df_launch['Brand'] == marca_lancamento]

    # Análise 1: Proporção geral
    st.markdown("### 📊 Proporção Geral: Lançamentos vs Produtos Antigos")
    proporcao = df_launch['Is_Launch'].value_counts()

    labels_map = {True: 'Lançamentos', False: 'Produtos Antigos'}
    fig_pizza = px.pie(
        values=proporcao.values,
        names=[labels_map.get(x, str(x)) for x in proporcao.index],
        title=f"Distribuição de Produtos - {marca_lancamento}",
        color=[labels_map.get(x, str(x)) for x in proporcao.index],
        color_discrete_map={'Lançamentos': '#FF6B6B', 'Produtos Antigos': '#4ECDC4'}
    )

    fig_pizza.update_traces(textposition='inside', textinfo='percent+label')
    st.plotly_chart(fig_pizza, use_container_width=True)

    # Análise 2: Lançamentos por categoria
    st.markdown("### 📈 Taxa de Lançamento por Categoria")
    lancamentos_categoria = df_launch.groupby('Product_Category')['Is_Launch'].agg(['sum', 'count'])
    lancamentos_categoria['taxa_lancamento'] = (
            lancamentos_categoria['sum'] / lancamentos_categoria['count'] * 100).round(1)
    lancamentos_categoria = lancamentos_categoria.sort_values('taxa_lancamento', ascending=True)

    fig_barras = px.bar(
        x=lancamentos_categoria['taxa_lancamento'],
        y=lancamentos_categoria.index,
        orientation='h',
        labels={'x': 'Taxa de Lançamento (%)', 'y': 'Categoria'},
        title=f"Percentual de Lançamentos por Categoria - {marca_lancamento}",
        color=lancamentos_categoria['taxa_lancamento'],
        color_continuous_scale='RdYlGn'
    )
    fig_barras.update_layout(height=600, showlegend=False)
    st.plotly_chart(fig_barras, use_container_width=True)

# Rodapé
st.markdown("---")
st.markdown(" **Ferramenta de Benchmarking de Mercado** | Desenvolvido por Misael 💙")