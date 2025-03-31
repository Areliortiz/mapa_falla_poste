import os
import pandas as pd
import base64
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
from dash import dash_table

import dash_leaflet as dl
from PIL import Image
from io import BytesIO
import geopandas as gpd

# ----------------------------- #
# Cargar datos desde el Excel
# ----------------------------- #
#archivo_excel = "E:/EDITH/julio/Reporte_Sin conectividad 28_01/Base_sin_filtro/Reporte Cámaras Sin conectividad 28_01.xlsx"
archivo_excel = "datos_fallas.xlsx"

ruta_imagenes = "E:/EDITH/julio/Reporte_Sin conectividad 28_01/Imagenes"
df = pd.read_excel(archivo_excel, sheet_name=1) # lee la hoja 1 de mi archivo (inicia en 0)


# Cargar los polígonos
# gdf_colonias = gpd.read_file("E:/EDITH/julio/MAPA_FALLAS/assets/Poligonos/colonias.shp")
# gdf_sectores = gpd.read_file("E:/EDITH/julio/MAPA_FALLAS/assets/Poligonos/sectores.shp")
# gdf_alcaldias = gpd.read_file("E:/EDITH/julio/MAPA_FALLAS/assets/Poligonos/alcaldias.shp")
# gdf_C2 = gpd.read_file("E:/EDITH/julio/MAPA_FALLAS/assets/Poligonos/C2.shp")
gdf_colonias = gpd.read_file("Poligonos/colonias.shp")
gdf_sectores = gpd.read_file("Poligonos/sectores.shp")
gdf_alcaldias  = gpd.read_file("Poligonos/alcaldias.shp")
gdf_C2 = gpd.read_file("Poligonos/c2.shp")

#print(gdf_alcaldias.head)
#print(gdf_alcaldias[["id_distrit"]].head())  # Verificar si la columna tiene los nombres correctos
#print(gdf_alcaldias.dtypes)  # Verificar el tipo de dato de cada columna


# ----------------------------- #
# Cargar la imagen de la rosa de los vientos
# ----------------------------- #
ruta_rosa_vientos = "puntos_cardinales_ajustado2.png"
def encode_rosa_vientos(image_path):
    try:
        with open(image_path, "rb") as img_file:
            return f"data:image/png;base64,{base64.b64encode(img_file.read()).decode()}"
    except FileNotFoundError:
        print(f"Error: No se encontró la imagen en {image_path}")
        return ""



# Verificar que las columnas necesarias existen
if not {'ID', 'LATITUD', 'LONGITUD', 'TIPO DE POSTE', 'FALLA'}.issubset(df.columns):
    raise ValueError("El archivo Excel debe contener las columnas: ID, LATITUD, LONGITUD, TIPO DE POSTE, FALLA.")

# Crear un diccionario de imágenes en la carpeta
base_url = "https://raw.githubusercontent.com/Areliortiz/mapa_falla_poste/main/imagenes/"
imagenes_dict = {
    str(row["ID"]): f"{base_url}{row['ID']}.jpg"
    for _, row in df.iterrows()
}



#----------------------------#
#funciion para generar etiquetas y asignar colores
#----------------------------#
# Definir colores según el tipo de poste
colores = ["blue", "red", "gray", "green", "purple", "orange",  "magenta","black"]
# Obtener fallas únicas, eliminando NaN o valores nulos
fallas_unicas = df["FALLA"].dropna().unique().tolist()
#print(fallas_unicas)
# Asignar colores a cada falla, asegurando que cada una tenga su color único
tipo_falla_colors= {fallas_unicas[i]: colores[i % len(colores)] for i in range(len(fallas_unicas))}


# ----------------------------- #
# Función para convertir a polígonos de Dash Leaflet
# ----------------------------- #

def convertir_a_poligonos(gdf, nombre_columna, color):
    
    # Lista para almacenar cada polígono con su tooltip
    features = []
    
    for feature in gdf.__geo_interface__["features"]:
        nombre = feature["properties"].get(nombre_columna, "Desconocido")
        
        features.append(
            dl.GeoJSON(
                data={"type": "FeatureCollection", "features": [feature]},
                options={"style": {"color": color, "fillOpacity": 0, "weight": 2}},
                hoverStyle={"weight": 4, "color": "black", "fillOpacity": 0.7},  # Efecto hover
                children=[
                    dl.Tooltip(nombre)  # Tooltip individual para cada polígono
                ]
            )
        )
    
    return features




#----------------------------#
#funciion para crear taabla inferior derecha
#----------------------------#
#generamos tabla
tabla_fallas = df.pivot_table(index="ALCALDÍA", columns="FALLA", aggfunc="size",fill_value=0)
#agregamos tototales
tabla_fallas["TOTAL"]=tabla_fallas.sum(axis=1)
#colocamos la columna "ALCALDIA" para que no sea indice
tabla_fallas.reset_index(inplace=True)




# ----------------------------- #
# Función para convertir imágenes a base64
# ----------------------------- #
import requests



def encode_image(image_url):
    try:
        response = requests.get(image_url)
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content))
            img.thumbnail((200, 150))
            buffered = BytesIO()
            img.save(buffered, format="JPEG")
            return base64.b64encode(buffered.getvalue()).decode()
        else:
            print(f"No se pudo cargar la imagen: {image_url}")
    except Exception as e:
        print(f"Error al cargar imagen: {e}")
    return ""


# ----------------------------- #
# Crear la aplicación Dash
# ----------------------------- #
app = dash.Dash(__name__, suppress_callback_exceptions=True)

app.layout = html.Div([

    # Contenedor para checklist con título
    html.Div([
        # Contenedor del título
        html.Div("TIPO DE FALLA", style={
            'backgroundColor': 'rgb(159, 34, 64)',  # Color rojo vino de la cabecera
            'color': 'rgb(188, 149, 92)',  # Texto dorado 
            'fontSize': '20px',  # Tamaño de la letra
            'fontWeight': 'bold',  # Negrita
            'textAlign': 'center',  # Centrado
            'padding': '10px',  # Espaciado interno
            'borderRadius': '10px 10px 0px 0px'
        }),

        # Contenedor checklist
        html.Div([
            dcc.Checklist(
                id='falla-checklist',
                options=[{'label': falla, 'value': falla} for falla in df['FALLA'].unique()],
                value=[],  # Selecciona todas por defecto
                inline=False,  # Asegurar que las opciones se vean en vertical
                labelStyle={"display": "block", "margin-bottom": "8px"},  # Espacio entre opciones
                style={
                    'color': 'black',
                    'fontSize': '15px',
                    'fontFamily': 'Arial, sans-serif'
                }
            )
        ], style={
            'backgroundColor': 'rgb(248, 249, 250)',  # Fondo 
            'padding': '15px',  # Espaciado interno
            'borderRadius': '0px 0px 10px 10px',  # Bordes redondeados abajo
            'boxShadow': '2px 2px 5px rgba(0,0,0,0.3)',  # Sombra suave
        })

    ], style={
        'position': 'absolute',
        'top': '20px', 'right': '250px',
        'width': '300px',
        'borderRadius': '10px',
        'overflowY': 'scroll',
        'maxHeight': '500px',
        'zIndex': '1000'
    }), 


    #tabla de los NOK
    html.Div([
        
        dash_table.DataTable(
            id="tabla_de_fallas",
            columns=[{"name": col, "id": col} for col in tabla_fallas.columns],
            data=tabla_fallas.to_dict("records"),
              
            style_table={'height': '600px', 'overflowX': 'auto'},  # Ajuste automático
            style_cell={
                'textAlign': 'center', 'padding': '8px',
                'fontSize': '12px', 'border': '1px solid black','padding': '5px',  
                'minWidth': '60px', 'maxWidth': '60px', 'width': '80px',
                #'whiteSpace': 'normal'  # Permite saltos de línea
            },
            style_header={'backgroundColor': 'rgb(159, 34, 64)', 
                        'textAlign': 'center',
                        'height': '90px',  # Aumenta la altura del encabezado
                        'padding': '8px',
                        'color': 'rgb(188, 149, 92)',
                        #'display': 'flex',  # Asegura que el contenido se distribuya dentro de la celda
            
                        ##'overflowWrap': 'break-word',  # Evita desbordes de texto
                        'fontSize': '10px', 
                        'lineHeight': '12px',  # Reduce el espaciado entre líneas
                        'whiteSpace': 'normal',  # Permite que el texto haga saltos de línea
                        }

        )
    ],style={
        'position': 'absolute',
        'bottom':'100px',
        'right': '20px',
        'width': 'auto',
        'borderRadius': '10px',
        
        'maxHeight': '500px',
        'zIndex': '1000'
    }),

    ## etiquta de colres(superior derecha)
    html.Div([
        #encabezado
        html.Div("TIPO DE FALLA", style={
            'backgroundColor': 'rgb(159, 34, 64)',  # Color de encabezado
            'color': 'rgb(188, 149, 92)',  # Color de texto
            'fontSize': '18px',
            'fontWeight': 'bold',
            'textAlign': 'center',
            'padding': '8px',
            'borderRadius': '10px 10px 0px 0px'
        }),
        #contenido
        html.Div([
            html.Div([
                html.Div(style={
                    "backgroundColor": color,
                    "width": "15px",
                    "height": "15px",
                    "display": "inline-block",
                    "marginRight": "10px",
                    "borderRadius": "3px"
                }),
                html.Span(tipo, style={"fontSize": "14px"})

            ], style={"display": "flex", "alignItems": "center", "marginBottom": "5px"}) 
            for tipo, color in tipo_falla_colors.items()
        ], style={
            'padding': '10px',
            'backgroundColor': 'white',
            'borderRadius': '0px 0px 10px 10px',
            'boxShadow': '2px 2px 5px rgba(0,0,0,0.3)',
        })

    ], style={
        'position': 'absolute',
        'top': '20px', 'right': '20px',
        'width': '200px',
        'borderRadius': '10px',
        'zIndex': '1000'
    }),

    #"etiqueta de filtro"
    html.Div([
        html.Div("Seleccionar Polígonos", style={
            'backgroundColor': 'rgb(159, 34, 64)',
            'color': 'rgb(188, 149, 92)',
            'fontSize': '18px',
            'fontWeight': 'bold',
            'textAlign': 'center',
            'padding': '8px',
            'borderRadius': '10px 10px 0px 0px'
        }),
        html.Div([ 
            dcc.Checklist(
                id="seleccionar-poligonos",
                options=[
                    {"label": "Colonias", "value": "Colonia"},
                    {"label": "Sectores", "value": "Sector"},
                    {"label": "Alcaldías", "value": "Alcaldia"},
                    {"label": "C2", "value": "C2"}],
                value=[],  # Ninguno seleccionado por defecto
                inline=False,  # Asegurar que las opciones se vean en vertical
                labelStyle={"display": "block", "margin-bottom": "4px",
                            "lineHeight": "5px"},  # Reduce la altura entre líneas},  # Espacio entre opciones
                style={
                    'color': 'black',
                    'fontSize': '12px',
                    'fontFamily': 'Arial, sans-serif'
                }
            )     
    ], style={
            'backgroundColor': 'rgb(248, 249, 250)',  # Fondo 
            'padding': '15px',  # Espaciado interno
            'borderRadius': '0px 0px 10px 10px',  # Bordes redondeados abajo
            'boxShadow': '2px 2px 5px rgba(0,0,0,0.3)',  # Sombra suave
            'maxHeight': '80px',
        })

    ], style={
        'position': 'absolute',
        'bootom': '20px', 'left': '20px',
        'width': '150px',
        'borderRadius': '10px', 
        'maxHeight': '200px',
        'zIndex': '500'
    }), 
    # Mapa 
    html.Div([
        dl.Map(
            id="mapa",
            style={'width': '100vw', 'height': '100vh'},
            center=[19.4326, -99.1332], 
            zoom=12,
            children=[dl.TileLayer()]
        )
    ], style={'position': 'absolute', 'top': '0', 'left': '0', 'right': '0', 'bottom': '0'}),

    html.Img(
        src=encode_rosa_vientos(ruta_rosa_vientos),
        style={
            'position': 'absolute',
            'bottom': '30px',
            'left': '30px',
            'width': '200px',
            'zIndex': '1000'
        }
    )

])

# ----------------------------- #
# Callback para actualizar el mapa según el filtro de fallas
# ----------------------------- #    
@app.callback(
    [
        Output("mapa", "children"),
        Output("mapa", "key")
    ],
    [
        Input("falla-checklist", "value"),
        Input("seleccionar-poligonos", "value")
    ]
)
def actualizar_mapa(fallas_seleccionadas, poligonos_seleccionados):
    
    capas_mapa = [dl.TileLayer()]  # Base del mapa

    # ---------------------------------------
    # Agregar marcadores según fallas seleccionadas
    # ---------------------------------------
    if fallas_seleccionadas:
        df_filtrado = df[df["FALLA"].isin(fallas_seleccionadas)]
        
        for _, row in df_filtrado.iterrows():
            lat, lon = row["LATITUD"], row["LONGITUD"]
            id_bct_o = str(row["ID"])
            tipo_poste = row["TIPO DE POSTE"]
            tipo_falla = row["FALLA"]

            # Obtener color por tipo de falla
            color = tipo_falla_colors.get(tipo_falla, "white")

            # Obtener imagen de la falla (si existe)
            imagen_path = imagenes_dict.get(id_bct_o, None)
            img_base64 = encode_image(imagen_path) if imagen_path else ""

            # Contenido del popup
            popup_content = html.Div([
                html.Img(src=f"data:image/jpeg;base64,{img_base64}", width="220px", height="150px", style={'borderRadius': '5px'}) if img_base64 else "",
                html.P(f"Tipo de poste: {tipo_poste}"),
                html.P(f"ID: {id_bct_o}"),
                html.P(f"Falla: {tipo_falla}")
            ], style={'textAlign': 'center'})

            capas_mapa.append(
                dl.CircleMarker(
                    center=(float(lat), float(lon)),
                    radius=6,
                    color=color,
                    fill=True,
                    fillOpacity=0.8,
                    children=[dl.Popup(popup_content)]
                )
            )

    # ---------------------------------------
    # Agregar polígonos según selección del usuario
    # ---------------------------------------
    if poligonos_seleccionados:
        if "Colonia" in poligonos_seleccionados:
            capas_mapa.extend(convertir_a_poligonos(gdf_colonias, "NOM_ASENTA", color="purple"))
            

        if "Sector" in poligonos_seleccionados:
            capas_mapa.extend(convertir_a_poligonos(gdf_sectores, "cuadrante", color="red"))

        if "Alcaldia" in poligonos_seleccionados:
            capas_mapa.extend(convertir_a_poligonos(gdf_alcaldias, "sector", color="blue"))

        if "C2" in poligonos_seleccionados:
            capas_mapa.extend(convertir_a_poligonos(gdf_C2, "distrito", color="green"))

    return capas_mapa, str(len(capas_mapa))  # Agregamos un valor único para "key"

# ----------------------------- #
# Ejecutar la aplicación
# ----------------------------- #
if __name__ == '__main__':
    app.run(debug=True)