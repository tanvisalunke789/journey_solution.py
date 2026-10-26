
import pandas as pd#(s)
import os#(s)
from sklearn.preprocessing import OneHotEncoder#(s)

class Journey:#(s) 
 
    # ---Section 1 --- #
 
    #(Question 1)
    def prepare_csv_data(self,df_1083,df_1415):#(s)


        answers_dir = os.path.join(os.path.dirname(__file__), "student_answer_csvs")#(s)
        os.makedirs(answers_dir, exist_ok=True)#(s)
        output_path = os.path.join(answers_dir, "question1.csv")#(s)

        df_1083.columns = df_1083.columns.str.strip()
        df_1415.columns = df_1415.columns.str.strip()

        df_1083["Date"] = pd.to_datetime(
            df_1083["Date"], dayfirst=True, errors="coerce"
        )
        df_1415["Date"] = pd.to_datetime(
            df_1415["Date"], dayfirst=True, errors="coerce"
        )

        df_1083["Date"] = df_1083["Date"].dt.strftime("%d/%m/%Y %H:%M:%S.%f").str[:-3]
        df_1415["Date"] = df_1415["Date"].dt.strftime("%d/%m/%Y %H:%M:%S.%f").str[:-3]

        df_merged = pd.concat([df_1083, df_1415], ignore_index=True)
        df_merged.to_csv(output_path, index=False)

        return df_merged.head(10).itertuples(index=False, name=None)

        

    #(Question 2)
    def prepare_csv_json_data(self,df_q1,collection):#(s)
        """
                Integrate the traffic and weather datasets. A key for integration needs to be identified for this purpose. Ensure both fields (used as key for the integration) are properly formatted and aligned in terms of date/time granularity.
                To enable integration, check whether aggregation of any of the involved datasets needs to be performed and perform it, if necessary. 
                
                For each time interval:
                    Compute averages for all relevant numeric columns (e.g., Headway, Gap, Speed).
                    Replace individual vehicle-level data with these aggregated values.
                    Count the number of vehicles and include this as a Vehicle Count column.

                Harmonise categorical values where necessary:
                For example, merge directional values such as ‘North’ and ‘Northeast’ into a single category called ‘NorthernQuadrant’, and assign it a code of ‘1’.
        
                Returns: Tuple: [ ('local_time', 'StartSite ID', 'EndSite ID', 'Direction', 'Direction Name', 'AVG Headway (s)', 'AVG Gap (s)', 'AVG Speed (mph)', 'Vehicle Count', 'city', 'position', 'weather_conditions', 'temperature', 'pressure', 'wind_speed', 'humidity'),
                                 ('01/01/2020 00:00:00.000', 1000, 2000, 1, 'NorthernQuadrant', 15.500000, 14.700000, 39.876543, 500, 'SampleCity', '16.2228,-1.2150', 'Clear', 10.0, 1012, 4.0, 65), 
                                 ('03/08/2018 18:20:03.000', 1111, 1515, 1, 'NorthQuadrant', 28.316009, 28.118414, 36.563302, 516, 'Leicester', '11.4808,-2.2300', 'Snow', 2.6, 992, 0.7, 77), ,...]
        """
        answers_dir = os.path.join(os.path.dirname(__file__), "student_answer_csvs")#(s)
        os.makedirs(answers_dir, exist_ok=True)#(s)
        output_path = os.path.join(answers_dir, "question2.csv")#(s) 

       
        # standardizing of traffic timestamps
        df = df_q1.copy()
        df.columns = df.columns.str.strip()

        df["Date"] = pd.to_datetime(
            df["Date"], dayfirst=True, errors="coerce"
        )
        df = df.dropna(subset=["Date"])
        df["local_time"] = df["Date"].dt.floor("h")

        # harmonizing the directions
        direction_map = {
            "North": ("NorthernQuadrant", 1),
            "Northeast": ("NorthernQuadrant", 1),
            "NorthEast": ("NorthernQuadrant", 1),
            "Northwest": ("NorthernQuadrant", 1),
            "NorthWest": ("NorthernQuadrant", 1),
            "South": ("SouthernQuadrant", 2),
            "Southeast": ("SouthernQuadrant", 2),
            "SouthEast": ("SouthernQuadrant", 2),
            "Southwest": ("SouthernQuadrant", 2),
            "SouthWest": ("SouthernQuadrant", 2),
            "East": ("EasternQuadrant", 3),
            "West": ("WesternQuadrant", 4)
        }

        def get_direction(value):
            value = str(value).strip()
            if value in direction_map:
                return direction_map[value]
            value_lower = value.lower()
            if value_lower.startswith("north"):
                return ("NorthernQuadrant", 1)
            if value_lower.startswith("south"):
                return ("SouthernQuadrant", 2)
            if value_lower.startswith("east"):
                return ("EasternQuadrant", 3)
            if value_lower.startswith("west"):
                return ("WesternQuadrant", 4)
            return (value, 0)

        direction_values = df["Direction Name"].apply(get_direction)
        df["Direction Name"] = direction_values.apply(lambda x: x[0])
        df["Direction"] = direction_values.apply(lambda x: x[1])

        # aggregated the traffic
        group_cols = ["local_time", "Direction", "Direction Name"]

        df_traffic = df.groupby(
            group_cols, dropna=False
        ).agg(
            **{
                "AVG Headway (s)": ("Headway (s)", "mean"),
                "AVG Gap (s)": ("Gap (s)", "mean"),
                "AVG Speed (mph)": ("Speed (mph)", "mean"),
                "Vehicle Count": ("Site ID", "size")
            }
        ).reset_index()

        for col in ["AVG Headway (s)", "AVG Gap (s)", "AVG Speed (mph)"]:
            df_traffic[col] = df_traffic[col].round(6)

        df_traffic["StartSite ID"] = 1083
        df_traffic["EndSite ID"] = 1415

        # to read documents from mongodb
        weather_docs = list(collection.find({}, {"_id": 0}))

        def get_nested(document, *keys):
            for key in keys:
                value = document
                try:
                    for part in key.split("."):
                        value = value[part]
                    return value
                except (KeyError, TypeError):
                    continue
            return None

        weather_rows = []

        for doc in weather_docs:
            timestamp = get_nested(
                doc, "local_time", "datetime", "date",
                "dt_txt", "timestamp", "dt", "time"
            )

            if timestamp is None:
                continue

            # conversion of timestamps
            if isinstance(timestamp, (int, float)):
                weather_time = pd.to_datetime(timestamp, unit="s", errors="coerce")
            else:
                weather_time = pd.to_datetime(timestamp, errors="coerce")

            if pd.isna(weather_time):
                continue

            weather_condition = get_nested(
                doc, "weather_conditions", "weather.description",
                "weather.0.main", "weather.0.description"
            )

            if isinstance(weather_condition, list):
                weather_condition = (
                    weather_condition[0].get("main")
                    if weather_condition and isinstance(weather_condition[0], dict)
                    else None
                )

            weather_rows.append({
                "local_time": weather_time.floor("h"),
                "city": get_nested(doc, "city", "name"),
                "position": get_nested(doc, "position"),
                "weather_conditions": weather_condition,
                "temperature": get_nested(doc, "temperature", "main.temp"),
                "pressure": get_nested(doc, "pressure", "main.pressure"),
                "wind_speed": get_nested(doc, "wind_speed", "wind.speed"),
                "humidity": get_nested(doc, "humidity", "main.humidity")
            })

        df_weather = pd.DataFrame(weather_rows)

        weather_cols = [
            "local_time", "city", "position", "weather_conditions",
            "temperature", "pressure", "wind_speed", "humidity"
        ]

        if df_weather.empty:
            df_weather = pd.DataFrame(columns=weather_cols)
        else:
            df_weather = df_weather.groupby(
                "local_time", as_index=False
            ).agg({
                "city": "first",
                "position": "first",
                "weather_conditions": "first",
                "temperature": "mean",
                "pressure": "mean",
                "wind_speed": "mean",
                "humidity": "mean"
            })

        # extracting only aggregated traffic
        df_merged = pd.merge(
            df_traffic,
            df_weather,
            on="local_time",
            how="left"
        )

        # formatting the timestamps and arranging columns
        df_merged["local_time"] = (
            df_merged["local_time"]
            .dt.strftime("%d/%m/%Y %H:%M:%S.%f")
            .str[:-3]
        )

        column_order = [
            "local_time", "StartSite ID", "EndSite ID",
            "Direction", "Direction Name",
            "AVG Headway (s)", "AVG Gap (s)", "AVG Speed (mph)",
            "Vehicle Count", "city", "position", "weather_conditions",
            "temperature", "pressure", "wind_speed", "humidity"
        ]

        df_merged = df_merged[column_order]
        df_merged = df_merged.sort_values("local_time").reset_index(drop=True)

        # saving the ouput
        df_merged.to_csv(output_path, index=False, float_format="%.6f")

        return list(df_merged.head(10).itertuples(index=False, name=None))


    #(Question 3)
    def prepare_csv_relational_data(self,conn,df_q2):#(s) 
        """
            Extract the relevant site and distance data from the SQLite database, specifically for the route from origin site 1083 to destination site 1415. It is worth pointing out that the distance data values appearing in the database are given in km.
            Join this data with the CSV file resulting from Task 2. The result should be a single CSV file that includes all previously integrated traffic and weather data, along with the distance between the two sites.
         
            Returns: Tuple: [('local_time', 'StartSite ID', 'EndSite ID', 'Distance', 'Direction', 'Direction Name', 'AVG Headway (s)', 'AVG Gap (s)', 'AVG Speed (mph)', 'Vehicle Count', 'city', 'position', 'weather_conditions', 'temperature', 'pressure', 'wind_speed', 'humidity'),
                              ('01/01/2020 00:00:00.000', 1000, 2000, 2.500000, 1, 'NorthQuadrant', 15.000000, 14.800000, 40.123456, 500, 'SampleCity', '00.0000,00.0000', 'Clear', 10.0, 1010, 5.0, 60),
                              ('09/15/2019 14:30:00.000', 1157, 1389, 2.034512, 0, 'EasternQuadrant', 29.782145, 29.615907, 35.482199, 472, 'Leeds', '53.8008,-1.5491', 'Rain', 3.1, 987, 0.5, 81), ....]
        """
        answers_dir = os.path.join(os.path.dirname(__file__), "student_answer_csvs")#(s)
        os.makedirs(answers_dir, exist_ok=True)#(s)
        output_path = os.path.join(answers_dir, "question3.csv")#(s) 

        
        # getting dist from site 1083 to site 1415 (in kms)
        distance_result = conn.execute(
            """
            SELECT Distance
            FROM DistanceBetweenSites
            WHERE StartSiteID = ? AND EndSiteID = ?
            """,
            (1083, 1415)
        ).fetchone()

        if distance_result is None:
            raise ValueError("Distance from site 1083 to site 1415 was not found.")

        # convert kms to miles 
        distance_miles = round(float(distance_result[0]) * 0.621371, 6)

        # adding route dist
        df_merged = df_q2.copy()
        df_merged["Distance"] = distance_miles

        # rearranging the col
        expected_columns = [
            "local_time",
            "StartSite ID",
            "EndSite ID",
            "Distance",
            "Direction",
            "Direction Name",
            "AVG Headway (s)",
            "AVG Gap (s)",
            "AVG Speed (mph)",
            "Vehicle Count",
            "city",
            "position",
            "weather_conditions",
            "temperature",
            "pressure",
            "wind_speed",
            "humidity"
        ]

        df_merged = df_merged[expected_columns]

    
        sort_dates = pd.to_datetime(
            df_merged["local_time"],
            format="%d/%m/%Y %H:%M:%S.%f",
            errors="coerce"
        )
        df_merged = (
            df_merged.assign(_sort_date=sort_dates)
            .sort_values("_sort_date")
            .drop(columns="_sort_date")
            .reset_index(drop=True)
        )

        # rounding calculated numeric val
        numeric_columns = [
            "Distance",
            "AVG Headway (s)",
            "AVG Gap (s)",
            "AVG Speed (mph)"
        ]
        df_merged[numeric_columns] = df_merged[numeric_columns].round(6)

        
        df_merged.to_csv(
            output_path,
            index=False,
            float_format="%.6f"
        )

    
        return [tuple(df_merged.columns)] + list(
            df_merged.head(10).itertuples(index=False, name=None)
        )


        

    #(Question 4)
    def prepare_final_data(self,df_q3,JT_archive):#(s) 
        """
            Join the CSV file from Question 3 with the journey time archive file. A join key needs to be identified for this purpose.
            The result should be a single CSV file that is going to be build that includes all previously integrated traffic, weather, and site data, along with the corresponding Journey Time values.
            
            Returns: Tuple:  [('local_time', 'StartSite ID', 'EndSite ID', 'Journey Time', 'Distance', 'Direction', 'Direction Name', 'AVG Headway (s)', 'AVG Gap (s)', 'AVG Speed (mph)', 'Vehicle Count', 'city', 'position', 'weather_conditions', 'temperature', 'pressure', 'wind_speed', 'humidity'),
                             ('01/01/2020 00:00:00.000', 1000, 2000, 2.500000, 1, 'NorthQuadrant', 15.000000, 14.800000, 40.123456, 500, 'SampleCity', '00.0000,00.0000', 'Clear', 10.0, 1010, 5.0, 60, 0.1000),
                             ('11/23/2019 09:15:00.000', 1128, 1392, 2.045783, 0, 'WesternQuadrant', 21.487923, 21.264812, 37.104827, 812, 'Liverpool', '53.4084,-2.9916', 'Light Snow', -0.8, 1004, 4.3, 68, 0.0472), .... ]
        """
        answers_dir = os.path.join(os.path.dirname(__file__), "student_answer_csvs")#(s)
        os.makedirs(answers_dir, exist_ok=True)#(s)
        output_path = os.path.join(answers_dir, "question4.csv")#(s) 

        
        import pandas as pd

        
        df_final = df_q3.copy()
        df_journey = JT_archive.copy()

        # parsing timestamps
        df_final["_join_time"] = pd.to_datetime(
        df_final["local_time"],
        format="%m/%d/%Y %H:%M:%S.%f",
        errors="coerce"
        )

        df_journey["_join_time"] = pd.to_datetime(
            df_journey["local_time"],
            format="%d/%m/%Y %H:%M",
            errors="coerce"
        )

        # selecting journey time and join
        df_journey = df_journey[
            ["_join_time", "Journey Time"]
        ].drop_duplicates(subset=["_join_time"])

        df_final = df_final.merge(
            df_journey,
            on="_join_time",
            how="left",
            validate="one_to_one"
        )

        # rearranging col
        expected_columns = [
            "local_time",
            "StartSite ID",
            "EndSite ID",
            "Journey Time",
            "Distance",
            "Direction",
            "Direction Name",
            "AVG Headway (s)",
            "AVG Gap (s)",
            "AVG Speed (mph)",
            "Vehicle Count",
            "city",
            "position",
            "weather_conditions",
            "temperature",
            "pressure",
            "wind_speed",
            "humidity"
        ]

        df_final = df_final[expected_columns]

        
        df_final["_sort_time"] = pd.to_datetime(
        df_final["local_time"],
        format="%m/%d/%Y %H:%M:%S.%f",
        errors="coerce"
        )
        df_final = (
            df_final.sort_values("_sort_time")
            .drop(columns="_sort_time")
            .reset_index(drop=True)
        )

        
        numeric_columns = [
            "Journey Time",
            "Distance",
            "AVG Headway (s)",
            "AVG Gap (s)",
            "AVG Speed (mph)"
        ]
        df_final[numeric_columns] = df_final[numeric_columns].round(6)

        
        output_path = (
            "student_answer_csvs/question4.csv"
        )
        df_final.to_csv(
            output_path,
            index=False,
            float_format="%.6f"
        )

        
        return [tuple(df_final.columns)] + list(
            df_final.head(10).itertuples(index=False, name=None)
        )

      
    #(Question 5)
    def result_and_encode_data(self,df_q4):#(s)
        """
         	Apply one-hot encoding to the weather_conditions column in your dataset. This process will automatically convert each unique weather condition into a separate binary feature, allowing the model to interpret categorical weather data numerically.
            After encoding, select the following columns as input features for your machine learning model.
         
            Returns: Tuple:( ('local_time', 'StartSite ID', 'EndSite ID', 'Distance', 'AVG Speed (mph)', 'AVG Headway (s)', 'AVG Gap (s)', 'Vehicle Count', 'city', 'position', 'temperature', 'pressure', 'wind_speed', 'humidity', 'Journey Time', 'weather_Clear', 'weather_Cloudy', 'weather_Fog', 'weather_Heavy Rain', 'weather_Light Rain', 'weather_Mist', 'weather_Partly Cloudy', 'weather_Snow'),
                            ('01/01/2020 00:00:00.000', 1000, 2000, 2.500000, 40.123456, 15.000000, 14.500000, 500, 'SampleCity', '00.0000,00.0000', 10.0, 1010, 5.0, 60, 0.1000, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0),
                           ('10/12/2019 09:30:00.000', 1142, 1388, 2.037654, 37.214589, 21.583421, 21.302774, 796, 'Leeds', '53.8008,-1.5491', -0.9, 1003, 4.6, 67, 0.0483, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0), ..)

        """

        ohe = OneHotEncoder(sparse_output=False, drop=None) #(s)
        
        
        answers_dir = os.path.join(
            os.path.dirname(__file__), "student_answer_csvs"
        )
        os.makedirs(answers_dir, exist_ok=True)
        output_path = os.path.join(answers_dir, "question5.csv")

        
        df_final = df_q4.copy()

        
        df_final["_sort_time"] = pd.to_datetime(
            df_final["local_time"],
            format="%m/%d/%Y %H:%M:%S.%f",
            errors="coerce"
        )

        
        df_final = df_final.sort_values("_sort_time").reset_index(drop=True)
        df_final["local_time"] = df_final["_sort_time"].dt.strftime(
            "%d/%m/%Y %H:%M:%S.%f"
        ).str[:-3]

        #defining weather categpries
        weather_categories = [
            "Clear",
            "Cloudy",
            "Fog",
            "Heavy Rain",
            "Light Rain",
            "Mist",
            "Partly Cloudy",
            "Snow"
        ]

        # one hot encode the weather conditions
        ohe = OneHotEncoder(
            categories=[weather_categories],
            sparse_output=False,
            drop=None,
            handle_unknown="ignore",
            dtype=float
        )

        weather_values = (
            df_final["weather_conditions"]
            .fillna("Unknown")
            .astype(object)
            .to_numpy()
            .reshape(-1, 1)
        )

        encoded_array = ohe.fit_transform(weather_values)

        encoded_columns = [
            "weather_" + category
            for category in weather_categories
        ]

        df_encoded = pd.DataFrame(
            encoded_array,
            columns=encoded_columns,
            index=df_final.index
        )

        # adding encoded features
        df_final = pd.concat(
            [
                df_final.drop(
                    columns=["weather_conditions", "_sort_time"]
                ),
                df_encoded
            ],
            axis=1
        )

        # selecting features in req order
        expected_columns = [
            "local_time",
            "StartSite ID",
            "EndSite ID",
            "Distance",
            "AVG Speed (mph)",
            "AVG Headway (s)",
            "AVG Gap (s)",
            "Vehicle Count",
            "city",
            "position",
            "temperature",
            "pressure",
            "wind_speed",
            "humidity",
            "Journey Time",
            "weather_Clear",
            "weather_Cloudy",
            "weather_Fog",
            "weather_Heavy Rain",
            "weather_Light Rain",
            "weather_Mist",
            "weather_Partly Cloudy",
            "weather_Snow"
        ]

        df_final = df_final[expected_columns]

        
        numeric_columns = [
            "Distance",
            "AVG Speed (mph)",
            "AVG Headway (s)",
            "AVG Gap (s)",
            "Journey Time"
        ]
        df_final[numeric_columns] = df_final[numeric_columns].round(6)

        
        df_final.to_csv(
            output_path,
            index=False,
            float_format="%.6f"
        )

        
        return [tuple(df_final.columns)] + list(
            df_final.head(10).itertuples(index=False, name=None)
        )


