<template>
   <div>
      <b-container id="program" fluid v-if="this.login.is_login">
         <b-row style="padding: 20px; background-color: #222; margin-bottom: 20px;">
            <b-col>
               <h1 style="margin-left: auto; margin-right: auto; text-align: center; color: #fff;">Annotation job manager: Metrics</h1>
            </b-col>
         </b-row>
         <b-row>
            <!-- LEFT COLUMN -->
            <!-- List jobs -->
            <b-col cols="5">
               <b-card bg-variant="light">
                  <b-form-group
                     label="List jobs"
                     label-size="lg"
                     label-align-sm="top"
                     label-class="font-weight-bold pt-0"
                     class="mb-0"
                     >
                     <b-row>
                        <b-col cols="10">
                             <b-form-group id="filter_status_group" label="Filter by status: " label-for="filter_status">
                                  <b-form-select style="float: left;" @change="do_list_jobs" v-model="list_jobs.selected_status" :options="preferences_status_list_expanded" size="sm"></b-form-select>
                            </b-form-group>
                        </b-col>
                        <b-col>
                            <b-button @click="do_list_jobs" size="sm" style="float: right;">
                              Refresh
                           </b-button>
                       </b-col>
                       
                     </b-row>
                     <br>
                     <b-table 
                        id="table_jobs"
                        @row-clicked="load_metrics_job"
                        small
                        :items="list_jobs.jobs" 
                        :fields="[
                            { 
                                key: 'name', 
                                sortable: true,
                                formatter(value, key, item){
                                    return item.name + ' - ' + item.camera;
                                },
                                sortByFormatted: true,
                            }, 
                            { 
                                key: 'eye', 
                                label: '',
                                sortable: true,
                                formatter(value, key, item){
                                    return item.visible;
                                },
                                sortByFormatted: true,
                            }, 
                            {
                                key: 'priority', 
                                sortable: true,
                                formatter(value, key, item){
                                    return item.priority;
                                },
                                sortByFormatted: true,
                            }, 
                            {
                                key: 'status', 
                                sortable: true,
                                formatter(value, key, item){
                                    return item.status;
                                },
                                sortByFormatted: true,
                            }, 
                            { 
                                key: 'date', 
                                sortable: true,
                                formatter(value, key, item){
                                    return date_to_str(item.created_at);
                                },
                                sortByFormatted: true,
                            }, 
                            {
                                key: 'created_by', 
                                label: 'Author',
                                sortable: true,
                                formatter(value, key, item){
                                    return item.created_by_name;
                                },
                                sortByFormatted: true,
                            }
                        ]" 
                        striped 
                        responsive="sm"
                        ref="jobs_table"
                        :sort-by.sync="list_jobs.sort_by"
                        :sort-desc.sync="list_jobs.sort_desc"
                        :current-page="list_jobs.current_page"
                        :per-page="list_jobs.per_page"
                        >
                        <template v-slot:cell(eye)="row">
                            <v-icon name="eye" v-if="row.item.visible" style="width: 20px"></v-icon>
                            <v-icon name="eye-off" v-else style="width: 20px"></v-icon>
                        </template>
                        <template v-slot:cell(date)="row">
                           {{ date_to_str(row.item.created_at) }}
                        </template>
                        <template v-slot:cell(status)="row">
                           <b-row>
                              <b-col>
                                 <div v-if="row.item.cancel !== undefined && row.item.cancel">
                                    <b-button style="cursor: default;" size="sm" variant="primary" class="status_cancel">CANCEL</b-button>
                                    &nbsp; <small><small>({{ preferences.status_list[row.item.status] }})</small></small>
                                 </div>
                                 <div v-else>
                                    <b-button style="cursor: default; font-size: 8pt !important;" size="sm" variant="primary" :class="{['status_' + preferences.status_list[row.item.status]]: true}">{{ preferences.status_list[row.item.status] }}</b-button>
                                 </div>
                              </b-col>
                            </b-row>
                            <b-row>
                              <b-col>
                                 <span style="margin-left: 10px;">{{ (row.item.total_files > 0) ? Math.round((row.item.done_files / row.item.total_files) * 100) : 0 }} % </span>
                              </b-col>
                           </b-row>
                           <br>
                           <b-row v-if="row.item.status == preferences.status_list.indexOf('FTP_UPLOADING')">
                              <b-col>
                                 <b-button style="font-size: 8pt !important;" class="primary" @click="do_start_ftp_upload($event, row.item)">Start FTP job</b-button>
                              </b-col>
                           </b-row>
                        </template>
                        
                     </b-table>

                     <b-row>
                        <b-col sm="7" md="6" class="my-1" v-if="list_jobs.total > 0">
                            <b-pagination
                              v-model="list_jobs.current_page"
                              :per-page="list_jobs.per_page"
                              :total-rows="list_jobs.total"
                              align="fill"
                              size="sm"
                              class="my-0"
                            ></b-pagination>
                        </b-col>
                    </b-row>

                  </b-form-group>
               </b-card>
            </b-col>

            <!-- RIGHT COLUMN -->
            <b-col cols="7">
               <b-card bg-variant="light">
                  <b-form-group
                    v-if="this.curr_metric != null && this.curr_metric.type == 'job'"
                     :label="'Metrics of the ' + this.curr_metric.type + ': ' + this.curr_job.name"
                     label-size="lg"
                     label-align-sm="top"
                     label-class="font-weight-bold pt-0"
                     class="mb-0">
                    <b-row>
                        <b-col><b>Name:</b><br> <span style="text-transform: capitalize;">{{ this.curr_job.name }}</span></b-col>
                        <b-col><b>Camera:</b><br> <span style="text-transform: capitalize;">{{ this.curr_job.camera }}</span></b-col>
                        <b-col><b>Sport:</b><br> <span style="text-transform: capitalize;">{{ this.curr_job.sport }}</span></b-col>
                        <b-col><b>Status:</b><br> <span style="text-transform: capitalize;">{{ preferences.status_list[this.curr_job.status] }}</span></b-col>
                    </b-row>

                    <!-- TIMMINGS -->
                    <hr>
                    <b-row>
                        <b-col><b>Timmings:</b></b-col>
                    </b-row>
                    <b-row>
                        <b-col style="padding: 20px; background-color: #ccc">
                            <span><b>Total:</b> {{Math.round(curr_metric.data.timmings.avg.total)}} seg ({{ Math.round(curr_metric.data.timmings.sum.total) }} seg / {{curr_metric.data.timmings.count.total }} images) </span><br>
                            <span><b>Per annotator:</b></span><br>
                            <div>
                                <div v-for="(time, anno_name) in curr_metric.data.timmings.avg.annotators" :key="anno_name"><span style="margin-left: 10px;"><b>&bull; {{ anno_name }}:</b> {{Math.round(time)}} seg ({{ Math.round(curr_metric.data.timmings.sum.annotators[anno_name]) }} seg / {{curr_metric.data.timmings.count.annotators[anno_name] }} images)</span><br></div>
                            </div>
                        </b-col>
                    </b-row>

                    <!-- Class distribution -->
                    <hr>
                    <b-row>
                        <b-col><b>Class distribution:</b></b-col>
                        <br>
                        <div style="width: 100%; padding-left: 20px;">
                            Classes: <div class="distribution_buttons">
                            <b-button @click="click_distribution_classes($event, 'total')" size="sm" :class="{toggle_btn: true, active: curr_metric != null && curr_metric.view.distribution.annotator == 'total'}" variant="primary">All</b-button>
                                <b-button @click="click_distribution_classes($event, annotator_name)" v-for="(positions, annotator_name) in curr_metric.data.distribution.annotators" :key="annotator_name" size="sm" :class="{toggle_btn: true, active: curr_metric != null && curr_metric.view.distribution.annotator == annotator_name}" variant="primary">{{annotator_name}}</b-button>
                            </div>
                        </div>
                    </b-row>

                    <b-row>
                        <b-col style="padding: 20px; background-color: #ccc">
                            <div  v-if="curr_metric.data.distribution != null && Object.keys(curr_metric.data.distribution.total).length">
                                <GChart
                                    @ready="on_distribution_classes_ready"
                                    :settings="{ packages: ['corechart'] }"
                                    type="BarChart"
                                    :data="curr_metric.data.distribution_classes_dataframe"
                                    :options="distribution_options"
                                  />
                            </div>

                            <span v-else>
                                No classes distributions
                            </span>

                        </b-col>
                    </b-row>

                    <!-- HEATMAP POSITIONS -->
                    <hr>
                    <b-row>
                        <b-col><b>Heatmap:</b></b-col>
                        <br>
                        <div style="width: 100%; padding-left: 20px;">
                            Annotators: <div class="heatmap_buttons">
                                <b-button @click="click_heatmap($event, 'total', null)" size="sm" :class="{toggle_btn: true, active: curr_metric != null && curr_metric.view.heatmap.annotator == 'total'}" variant="primary">All</b-button>
                                <b-button @click="click_heatmap($event, annotator_name, null)" v-for="(positions, annotator_name) in curr_metric.data.heatmap.annotators" :key="annotator_name" size="sm" :class="{toggle_btn: true, active: curr_metric != null && curr_metric.view.heatmap.annotator == annotator_name}" variant="primary">{{annotator_name}}</b-button>
                            </div>
                        </div>
                        <br>
                        <div style="width: 100%; padding-left: 20px;">
                            Classes: <div class="heatmap_buttons">
                            <b-button @click="click_heatmap($event, null, 'total')" size="sm" :class="{toggle_btn: true, active: curr_metric != null && curr_metric.view.heatmap.class == 'total'}" variant="primary">All</b-button>
                            <b-button @click="click_heatmap($event, null, class_name)" v-for="(positions, class_name) in curr_metric.data.heatmap.total" :key="class_name" size="sm" :class="{toggle_btn: true, active: curr_metric != null && curr_metric.view.heatmap.class == class_name}" variant="primary">{{class_name}}</b-button>
                            </div>
                        </div>

                    </b-row>

                    <b-row>
                      <b-col>
                        Show Frame {{ parseInt(curr_metric.view.frames.current) + 1}}: <b-form-input id="range-1" v-model="curr_metric.view.frames.current" type="range" min="0" :max="curr_metric.view.frames.total - 1" @change="change_heatmap_frame"></b-form-input>
                      </b-col>
                    </b-row>

                    <b-row v-if="curr_metric.data.roi">
                      <b-col>
                        Toggle roi: &nbsp; <b-button class="btn-sm" :pressed.sync="curr_metric.view.show_roi"><span v-if="curr_metric.view.show_roi">Off</span><span v-else>On</span></b-button>
                      </b-col>
                    </b-row>
                    <br>

                    <b-row>
                        <b-col style="padding: 20px; background-color: #ccc">
                            <div id="heatmap_out">
                                <div id="heatmap_wrapper">
                                    <div id="heatmap_container">
                                        
                                    </div>
                                </div>
                                <canvas v-show="this.curr_metric.view.show_roi" id="heatmap_roi"></canvas>
                                <img :src="this.curr_metric.data.heatmap.sample" width="100%" style="width: 100%">
                            </div>
                        </b-col>
                    </b-row>

                    <!-- Timeline tags -->
                    <hr>
                    <b-row>
                        <b-col><b>Timeline activated frame tags:</b></b-col>
                    </b-row>

                    <b-row>
                        <b-col sm="3"><b>FPS:</b></b-col>
                        <b-col><b-form-input @input="change_fps" @change="change_fps" v-model="curr_metric.view.timeline.fps" placeholder="30"></b-form-input></b-col>
                    </b-row>
                    <br>

                    <b-row>
                        <b-col style="padding: 20px; background-color: #ccc">
                            <div  v-if="curr_metric.data.timeline != null && curr_metric.data.timeline.length > 0">
                                <GChart
                                    @ready="on_timeline_ready"
                                    :settings="{ packages: ['timeline'] }"
                                    type="Timeline"
                                    :data="curr_metric.data.timeline_dataframe"
                                    :options="timeline_options"
                                  />
                            </div>

                            <span v-else>
                                No frame tags
                            </span>

                        </b-col>
                    </b-row>

                    <br>
                    <b-row>
                        <b-col><b>Distribution frame tags:</b></b-col>
                    </b-row>

                    <b-row>
                        <b-col style="padding: 20px; background-color: #ccc">
                            <div  v-if="curr_metric.data.timeline != null">
                                <GChart
                                    @ready="on_distribution_frame_tags_ready"
                                    :settings="{ packages: ['corechart'] }"
                                    type="BarChart"
                                    :data="curr_metric.data.distribution_frame_tags_dataframe"
                                    :options="distribution_frame_tags_options"
                                  />
                            </div>

                            <span v-else>
                                No frame tags distributions
                            </span>

                        </b-col>
                    </b-row>


                  </b-form-group>
               </b-card>
            </b-col>

         </b-row>
      </b-container>
      <!-- Login -->
      <b-container id="program" fluid style="height: 100vh" v-else>
         <div style="width: 400px; height: 400px; position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);">
            <b-card bg-variant="light">
               <b-form-group
                  label="Login"
                  label-size="lg"
                  label-align-sm="top"
                  label-class="font-weight-bold pt-0"
                  class="mb-0"
                  >
                  <b-row class="mb-2">
                     <b-col sm="5" class="text-sm-right"><b>Username:</b></b-col>
                     <b-col>
                        <b-form-input v-model="login.username" placeholder="Enter your username"></b-form-input>
                     </b-col>
                  </b-row>
                  <b-row class="mb-2">
                     <b-col sm="5" class="text-sm-right"><b>Password:</b></b-col>
                     <b-col>
                        <b-form-input type="password" v-model="login.password" placeholder="Enter your password"></b-form-input>
                     </b-col>
                  </b-row>
                  <b-button style="float: right;" @click="do_login" variant="primary">Login</b-button>
               </b-form-group>
               <span v-if="login.message != ''" style="color: #f00;">{{ login.message }}</span>
            </b-card>
         </div>
      </b-container>
   </div>
</template>

<script>
// import HelloWorld from './components/HelloWorld.vue'
import axios from 'axios';
import JQuery from 'jquery';
import h337 from 'heatmap.js';

//import Resumable from 'resumablejs';
const resum = require('./resumable');
const Resumable = resum.Resumable;
let $ = JQuery;
const uuidv4 = require('uuid/v4');
import Timeselector from 'vue-timeselector';
import {Endpoints} from './endpoints';

export default {
  name: 'app',
  components: {
    // HelloWorld
    Timeselector
  },
    data() {
        return {
            timeline_options: {
                width: '100%',
                hAxis: {
                    format: 'mm:ss',
                },
            },

            distribution_options: {
                width: '100%',
                bar: {groupWidth: "95%"},
                legend: { position: "none" },
            },

            distribution_frame_tags_options: {
                 width: '100%',
                bar: {groupWidth: "95%"},
                legend: { position: "none" },
            },


            curr_metric: null,
            curr_job: {
                name: ''
            },

            // List jobs
            list_jobs: {
                sort_by: 'date',
                sort_desc: true,
                current_page: 1,
                per_page: 10,
                total: 0,
                jobs: [],
                selected_status: 'None',
            },

            // Login
            login: {
                is_login: this.$cookie.get('token') != null,
                username: null,
                password: null,
                message: ''
            },

            // metrics
            metrics: {
                job_id: null,
                annotator_id: null,
                list: [],
            },

            // Pref
            preferences: {
                total_preprocess_steps: 0,
                total_postprocess_steps: 0,
                sports_list: [],
                sports_with_autolabeling_list: [],
                tags_list: [],
                frame_tags_list: [],
                status_list: ['FTP_UPLOADING', 'PREPROCESS', 'NOT_STARTED', 'IN_PROCESS', 'POSTPROCESS', 'FINISHED'],
                refresh_list_job: null,
                groups_list: ['ADMIN', 'ANNOTATOR'],
            },     
        }
    },

    methods: {
        date_to_str(date){
            if(date !== undefined && date['$date'] !== undefined){
                let m = new Date(date['$date']);
                let dateString =
                    m.getFullYear() + "/" +
                    ("0" + (m.getMonth()+1)).slice(-2) + "/" +
                    ("0" + m.getDate()).slice(-2) + " " +
                    ("0" + m.getHours()).slice(-2) + ":" +
                    ("0" + m.getMinutes()).slice(-2) + ":" +
                    ("0" + m.getSeconds()).slice(-2);

                return dateString;
            }
            return '-';
        },

        /*
            INIT FUNCTIONS
        */
        init_dashboard(){
            let self = this;
            this.send_request({endpoint: Endpoints.PREFERENCES.GET, method: 'GET', on_response: function(response){
                self.preferences.tags_list = response['data']['data']['tags'];
                self.preferences.frame_tags_list = response['data']['data']['frame_tags'];
                self.preferences.sports_list = response['data']['data']['sports'];
                self.preferences.sports_with_autolabeling_list = response['data']['data']['sports_with_autolabeling'];
                self.list_jobs.jobs = response['data']['data']['jobs'];
                self.list_jobs.total = self.list_jobs.jobs.length;

                if(self.$route.params != null && self.$route.params.job_id != null){
                    for(let i = 0; self.list_jobs.jobs.length; i++){
                        if(self.$route.params.job_id == self.list_jobs.jobs[i]._id.$oid && self.list_jobs.jobs[i].status >= self.preferences.status_list.indexOf("IN_PROCESS") ){
                            self.load_metrics_job(self.list_jobs.jobs[i]);
                        }
                    }
                }
            },
            on_error: this.login_error});
        },

        /*
            =============================
            MISC
            =============================
        */
        send_request(call_data){
            // endpoint, method, data_uri={}, data={}, on_response=function(){}, on_finish=function(){}, on_error=function(){}
            axios.defaults.withCredentials = false;
            let endpoint_with_data = call_data['endpoint'];
            if(call_data['data_uri'] != undefined)
                endpoint_with_data = endpoint_with_data + '?' + $.param(call_data['data_uri']);

            let headers = undefined;
            if(this.$cookie.get("token")){
                headers = {headers: { "Authorization": 'JWT ' + this.$cookie.get("token") }};
            }

            if(call_data['method'] == 'GET'){
                return axios.get(endpoint_with_data, headers)
                .then(response => {
                    if(call_data['on_response'] !== undefined)
                        call_data['on_response'](response);
                })
                .catch(error => {
                    if(call_data['on_error'] !== undefined)
                        call_data['on_error'](error);
                })
                .finally(() => {
                    if(call_data['on_finish'] !== undefined)
                        call_data['on_finish']();
                });
            }else if(call_data['method'] == 'POST'){
                return axios.post(endpoint_with_data, call_data['data'], headers)
                .then(response => {
                    if(call_data['on_response'] !== undefined)
                        call_data['on_response'](response);
                })
                .catch(error => {
                    if(call_data['on_error'] !== undefined)
                        call_data['on_error'](error);
                })
                .finally(() => {
                    if(call_data['on_finish'] !== undefined)
                        call_data['on_finish']();
                });
            }     
        },

        login_error(error){
            if(error.response == undefined || error.response['data'] == undefined || error.response['data']['error'] == undefined)
                return;

            if(error.response['data']['error'] == 'Invalid token'){
                this.login.is_login = false;
                this.login.message = 'Wrong token. Relogin.';
                this.$cookie.delete('token');
            }else if(error.response['data']['error'] == 'Bad Request' && error.response['data']['description'] == 'Invalid group'){
                this.login.is_login = false;
                this.login.message = 'Not allowed.';
                this.$cookie.delete('token');
            }else if(error.response['data']['error'] == 'Bad Request' && error.response['data']['description'] == 'Invalid credentials'){
                this.login.is_login = false;
                this.login.message = 'Wrong username or password.';
                this.$cookie.delete('token');
            }
        },

        /*
            =============================
            LOGIN
            =============================
        */
        do_login(){
            let self = this;
            this.send_request({endpoint: Endpoints.USERS.LOGIN, method: 'POST', data: {
                username: this.login.username,
                password: this.login.password,
                group: 0
            },
            on_response: function(response){
                self.login.is_login = true;
                self.login.message = 'Logged in successfully.'; 
                self.$cookie.set('token', response['data']['access_token']);
                self.init_dashboard();
            },

            on_error: this.login_error
            });
        },

        /*
            =============================
            JOBS
            =============================
        */
        /*
            LIST JOBS
        */
        do_list_jobs(){
            let old_show_idx = -1;
            for(let i = 0; i < this.list_jobs.jobs.length; i++){
                if(this.list_jobs.jobs[i]._showDetails){
                    old_show_idx = this.list_jobs.jobs[i]._id.$oid;
                }
            }
            let self = this;
            let data_axios = {
                endpoint: Endpoints.JOBS.LIST, 
                method: 'GET', 
                on_response: function(response){
                    self.list_jobs.jobs = response['data']['data'];
                    self.list_jobs.total = self.list_jobs.jobs.length;
                    
                    for(let i = 0; i < self.list_jobs.jobs.length; i++){
                        if(self.list_jobs.jobs[i]._id.$oid == old_show_idx){
                            self.$set(self.list_jobs.jobs[i], '_showDetails', true);
                        }else{
                            self.$set(self.list_jobs.jobs[i], '_showDetails', false);
                        }
                    }
                },
                on_error: function(error){
                    self.login_error(error);
                    if(error.response['data']['error'] == 'error_job_list'){
                        alert(error.response['data']['description']);
                    }
                }};
            if(this.list_jobs.selected_status != 'None'){
                data_axios['data_uri'] = {'status': this.preferences.status_list.indexOf(this.list_jobs.selected_status)};
            }
            this.send_request(data_axios);
        },

        /*
            =============================
            METRICS
            =============================
        */

        str_to_color(str) {
            let hash = 0;
            for (let i = 0; i < str.length; i++) {
                hash = str.charCodeAt(i) + ((hash << 5) - hash);
            }
            let colour = '#';
            for (let i = 0; i < 3; i++) {
                let value = (hash >> (i * 8)) & 0xFF;
                colour += ('00' + value.toString(16)).substr(-2);
            }
            return colour;
        },

        load_metrics_job(row){
            if(row.status < this.preferences.status_list.indexOf('IN_PROCESS')){
                alert("This job doesn't have metrics yet");
                return;
            }

            let self = this;
            this.send_request({
                endpoint: Endpoints.JOBS.METRICS,
                method: 'GET',
                data_uri: {
                    job_id: row._id.$oid
                },
                on_response: function(response){
                    let metrics = response.data.data;


                    self.curr_job = row;

                    // Parsing timeline
                    let aux_timeline = metrics.timeline;
                    metrics.timeline = self.create_timeline_frame_tags(aux_timeline);
                    metrics.distribution_timeline = self.create_distribution_frame_tags(aux_timeline);

                    self.curr_metric = {
                        type: 'job',
                        data: metrics,
                        view: {
                            heatmap: {
                                annotator: 'total',
                                class: 'total'
                            },

                            distribution: {
                                annotator: 'total'
                            },

                            timeline: {
                                fps: 1
                            },

                            frames: {
                                current: 0,
                                total: metrics.timmings.count.total
                            },

                            show_roi: true
                        }
                    };

                    // Set timeline (nothing to wait)
                    self.$set(self.curr_metric.data, 'timeline_dataframe', null);
                    self.$set(self.curr_metric.data, 'distribution_frame_tags_dataframe', null);

                    if(self.google_lib !== undefined){
                        self.create_timeline_dataframe(self.google_lib);
                        self.create_distribution_frame_tags_dataframe(self.google_lib);
                    }
                    
                    // Set heatmap (wait image)
                    $("#heatmap_out img").ready(function(){
                        self.create_heatmap();
                        self.create_roi();
                    });

                    // Set distribution (wait buttons)
                    self.$set(self.curr_metric.data, 'distribution_classes_dataframe', null);
                    $(".distribution_buttons").ready(function(){
                        self.create_distribution_classes();
                    });
                },

                on_error: function(error){
                    self.login_error(error);
                    if(error.response['data']['error'] == 'error_job_metrics'){
                        alert(error.response['data']['description']);
                    }
                }
            });
        },


        /*
            HEATMAP
        */
        create_roi(){
            let canvas = $("#heatmap_out canvas#heatmap_roi")[0];

            canvas.width = this.curr_metric.data.heatmap.size[0];
            canvas.height = this.curr_metric.data.heatmap.size[1];
            let ctx = canvas.getContext('2d');

            if(this.curr_metric.data.roi !== undefined && this.curr_metric.data.roi != null){
                ctx.beginPath();

                ctx.moveTo(this.curr_metric.data.roi[0][0], this.curr_metric.data.roi[0][1]);
                //let prev_pos = this.curr_metric.data.roi[0];
                for(let i = 1; i < this.curr_metric.data.roi.length; i++){
                    ctx.lineTo(this.curr_metric.data.roi[i][0], this.curr_metric.data.roi[i][1]);
                    //prev_pos = this.curr_metric.data.roi[i];
                }
                ctx.closePath();
                ctx.fillStyle = "rgba(255, 255, 0, 0.2)";
                ctx.fill();
                ctx.clip();
                ctx.strokeStyle = "rgba(255, 255, 0, 0.9)";
                ctx.stroke();
            }
        },
        set_heatmap(){
            this.clear_heatmap();
            this.curr_metric.data.heatmap_viewer.setData(this.transform_heatmap_to_px(this.curr_metric.data.heatmap_curr_data));
        },

        change_heatmap_frame(){
            let self = this;
             this.send_request({
                endpoint: Endpoints.JOBS.IMAGE_FRAME,
                method: 'GET',
                data_uri: {
                    job_id: this.curr_job._id.$oid,
                    frame_id: this.curr_metric.view.frames.current
                },
                on_response: function(response){
                    if(response['data']['data'] != null)
                        self.curr_metric.data.heatmap.sample = response['data']['data']['image'];
                },
                on_error: this.login_error
            });
        },

        create_heatmap(){
            let annotator = this.curr_metric.view.heatmap.annotator;
            let label = this.curr_metric.view.heatmap.class;
            let dict_heatmap;

            if (annotator == 'total'){
                dict_heatmap = this.curr_metric.data.heatmap.total;
            }else{
                dict_heatmap = this.curr_metric.data.heatmap.annotators[annotator];
            }

            if(label == 'total'){
                let max = 0; 
                let data = [];
                for(let key in dict_heatmap) {
                    let aux = this.create_heatmap_array(dict_heatmap[key]);
                    if(max < aux.max){
                        max = aux.max;
                    }
                    data = data.concat(aux.data);
                }

                this.curr_metric.data.heatmap_curr_data = {
                    max: max,
                    data: data
                };
            }else{
                this.curr_metric.data.heatmap_curr_data = this.create_heatmap_array(dict_heatmap[label]);
            }
            
            this.set_heatmap();
        },

        transform_heatmap_to_px(data_norm){
            let img = $("#heatmap_out img");
            let img_height = img.height();
            let img_width = img.width();

            let data = {
                max: data_norm.max,
                data: []
            };

            for(let i = 0; i < data_norm.data.length; i++){
                data.data.push({x: Math.round(data_norm.data[i].x * img_width), y: Math.round(data_norm.data[i].y * img_height), value: data_norm.data[i].value});
            }

            return data;
        }, 

        clear_heatmap(){
            $('#heatmap_container').html('');
            this.curr_metric.data.heatmap_viewer = h337.create({
                  container: $('#heatmap_container')[0]
                });
            // this.curr_metric.data.heatmap_viewer.setData({data:[]});
            // this.curr_metric.data.heatmap_viewer.removeData();
        },

        create_heatmap_array(positions){
            let max = 0;
            let data = [];
            for(let pos in positions){
                let fix_pos = pos.split('_');
                fix_pos[0] = parseInt(fix_pos[0]) / this.curr_metric.data.heatmap.size[0];
                fix_pos[1] = parseInt(fix_pos[1]) / this.curr_metric.data.heatmap.size[1];
                
                let value = positions[pos];
                if(max < value){
                    max = value;
                }
                data.push({x: fix_pos[0], y: fix_pos[1], value: value});
            }

            return {max: max, data: data};
        },

        click_heatmap(event, annotator, label){
            if(annotator != null){
                this.curr_metric.view.heatmap.annotator = annotator;
            }

            if(label != null){
                this.curr_metric.view.heatmap.class = label;
            }
            this.create_heatmap();
        },

        /*
            TIMELINE FRAME TAGS
        */
        change_fps(){
            if(this.google_lib !== undefined)
                this.create_timeline_dataframe(this.google_lib);
        },

        on_timeline_ready(chart, google) {
            this.google_lib = google;
            // now we have google lib loaded. Let's create data table based using it.
            this.create_timeline_dataframe(google);
        },

        create_timeline_frame_tags(timeline_data){
            let rows = [];
            for(let key in timeline_data){
                let timeline_each_tag = timeline_data[key];
                for(let i = 0; i < timeline_each_tag.length; i++){
                    let interval = timeline_each_tag[i];
                    rows.push([key, 
                        1000 * interval[0], 
                        1000 * interval[1]
                    ]);
                }
            }

            return rows;
        },

        create_timeline_dataframe(google) {
            const data = new google.visualization.DataTable();
            data.addColumn('string', 'Tag');
            data.addColumn('date', 'Start');
            data.addColumn('date', 'End');

            let fps = this.curr_metric.view.timeline.fps || 30;
            let aux = [];
            for(let i = 0; i < this.curr_metric.data.timeline.length; i++){
                let name = this.curr_metric.data.timeline[i][0];
                let start_time = new Date(this.curr_metric.data.timeline[i][1] / fps);
                let end_time = new Date(this.curr_metric.data.timeline[i][2] / fps);
                aux.push([name, start_time, end_time]);
            }

            data.addRows(aux);

            // Since the :data is reactive, we just need to update it's value
            this.$set(this.curr_metric.data, 'timeline_dataframe', data);   
        },

        /*
            DISTRIBUTION FRAME TAGS
        */
        on_distribution_frame_tags_ready(chart, google) {
            this.google_lib = google;
            // now we have google lib loaded. Let's create data table based using it.
            this.create_distribution_frame_tags_dataframe(google);
        },

        create_distribution_frame_tags(timeline_data) {
            let data_aux = [
                ["Class", "number", { role: "style" } ]
            ];
            for(let k in timeline_data){
                let acc = 0;
                for(let i = 0; i < timeline_data[k].length; i++){
                    let v = timeline_data[k][i];
                    acc += (v[1] - v[0]);              
                }
                data_aux.push([k, acc, this.str_to_color(k)]);
            }

            // Since the :data is reactive, we just need to update it's value
            return data_aux;
        },

        create_distribution_frame_tags_dataframe(google) {
            let data_aux = [
            ["Class", "number", { role: "style" } ]
            ];

            let data = google.visualization.arrayToDataTable(this.curr_metric.data.distribution_timeline);
            let view = new google.visualization.DataView(data);
            view.setColumns([0, 1, { 
                calc: "stringify",
                sourceColumn: 1,
                type: "string",
                role: "annotation" 
            }, 2]);

            // Since the :data is reactive, we just need to update it's value
            this.$set(this.curr_metric.data, 'distribution_frame_tags_dataframe', view);     
        },

        /*
            CLASS DISTRIBUTIONS
        */
       
        on_distribution_classes_ready(chart, google) {
            this.google_lib = google;
            // now we have google lib loaded. Let's create data table based using it.
            this.create_distribution_classes_dataframe(google);
        },

        create_distribution_classes_dataframe(google) {    
            let data_aux = [
            ["Class", "number", { role: "style" } ]
            ];
            for(let k in this.curr_metric.data.distribution_curr_data){
                data_aux.push([k, this.curr_metric.data.distribution_curr_data[k], this.str_to_color(k)]);
            }

            let data = google.visualization.arrayToDataTable(data_aux);
            let view = new google.visualization.DataView(data);
            view.setColumns([0, 1, { 
                calc: "stringify",
                sourceColumn: 1,
                type: "string",
                role: "annotation" 
            }, 2]);

            // Since the :data is reactive, we just need to update it's value
            this.$set(this.curr_metric.data, 'distribution_classes_dataframe', view);   
        },

        click_distribution_classes(event, annotator){
            if(annotator != null){
                this.curr_metric.view.distribution.annotator = annotator;
            }
            this.create_distribution_classes();
        },

        create_distribution_classes(){
            let annotator = this.curr_metric.view.distribution.annotator;

            if (annotator == null || annotator == 'total'){
                this.curr_metric.data.distribution_curr_data = this.curr_metric.data.distribution.total;
            }else{
                this.curr_metric.data.distribution_curr_data = this.curr_metric.data.distribution.annotators[annotator];
            }

            if(this.google_lib !== undefined){
                this.create_distribution_classes_dataframe(this.google_lib);
            }
        },
    },

    computed: {
        preferences_status_list_expanded(){
            let old_status = this.preferences.status_list.slice();
            old_status.splice(0, 0, 'None');
            return old_status;
        },

        preferences_expanded_sport_list(){
            return ["none"].concat(this.preferences.sports_list);
        }
    },

    mounted(){
        if(this.login.is_login){
            this.init_dashboard();
        } 
        let self = this;
        window.addEventListener("resize", function(){
            if(self.curr_metric != null && 
                self.curr_metric.type == 'job' &&
                self.curr_metric.data.heatmap_curr_data !== undefined && 
                self.curr_metric.data.heatmap_curr_data != null){
                self.create_roi();
                self.set_heatmap();    
            }
        });
        
        /*this.colors = [];
        for(let i = 0; i < 100; i++){
            this.colors.push('#' + Math.floor(Math.random() * 16777215).toString(16));
        }*/
    }
}
</script>

<style>
#app {
  font-family: 'Avenir', Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-align: center;
  color: #2c3e50;
  margin-top: 60px;
}

#heatmap_out{
    position: relative;
}

#heatmap_wrapper{
    position: absolute;
    z-index: 3;
    width:100%; 
    height:100%;
}

#heatmap_out canvas#heatmap_roi{
    position: absolute;
    z-index: 2;
    width:100%;
    height: 100%;
}
#heatmap_out img{
    z-index: 1;
    width:100%; 
    height:100%;
}

#heatmap_container{
    width:100%; 
    height:100%;
}
.heatmap_buttons, .distribution_buttons{
    padding: 10px 0px 10px 0px;
    display: inline-block;
}
.heatmap_buttons > button, .distribution_buttons > button{
    margin-left: 10px;
    text-transform: capitalize;
}

#table_jobs td{
    cursor: pointer;
}

.cancel{
    border: 2px solid #f00 !important;
}

.toggle_btn.btn{
    background-color: #888 !important;
}

.toggle_btn.btn.active{
    background-color: #222 !important;
}

/* status */
.btn.status_PREPROCESS, .btn.status_POSTPROCESS{
    background-color: #00f !important;
}
.btn.status_NOT_STARTED, .btn.status_cancel{
    background-color: #f00 !important;
}
.btn.status_IN_PROCESS{
    background-color: #ff0 !important;
    color: #000 !important;
}
.btn.status_FINISHED{
    background-color: #1a981a !important;
}

.active_btn{
    margin-left: auto; 
    margin-right: auto; 
    border-radius: 15px; 
    width: 15px; 
    height: 15px;
    border: 1px rgba(100, 100, 100, 50) solid; 
}
.active_btn.yes{
    background-color: #0f0; 
}
.active_btn.no{
    background-color: #f00; 
}
</style>
