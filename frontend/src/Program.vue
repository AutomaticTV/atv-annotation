<template>
    <div>
        <b-container id="program" fluid v-if="this.login.is_login">
            <b-row style="padding: 20px; background-color: #222; margin-bottom: 20px;">
                <b-col>
                    <h1 style="margin-left: auto; margin-right: auto; text-align: center; color: #fff;">Annotation job manager</h1>
                    <a href="/#/metrics" target="new"><b-button style="float: right;" variant="primary">Go to metrics</b-button></a>
                </b-col>
            </b-row>
            <b-row>
                <!-- LEFT COLUMN -->
                <!-- New Job -->
                <b-col cols="4">
                    <b-card bg-variant="light" v-if="new_job.step == 'progress'">
                        <b-form-group
                            label="New Job"
                            label-size="lg"
                            label-align-sm="top"
                            label-class="font-weight-bold pt-0"
                            class="mb-0"
                            >
                            <b-row>
                                <b-col>
                                    Uploading... {{ Math.round(this.new_job.progress_bar * 100) }}%
                                    <br>
                                    <div v-if="this.new_job.message != ''">
                                        <span style="color: #f00;">{{ this.new_job.message }}</span>
                                        <b-button @click="new_job.step='create'; do_new_job_clear(); " variant="primary">Create Again</b-button>
                                    </div>
                                    <div v-if="new_job.completed">
                                        Job updated successfully. 
                                        <br><br>
                                        <b-button @click="new_job.step='create'; do_new_job_clear(); " variant="primary">Create another</b-button>
                                    </div>
                                </b-col>
                            </b-row>
                        </b-form-group>
                    </b-card>
                    <b-card bg-variant="light" v-if="new_job.step == 'create'">
                        <b-form-group
                            label="New Job"
                            label-size="lg"
                            label-align-sm="top"
                            label-class="font-weight-bold pt-0"
                            class="mb-0"
                            >
                            <!-- Job name -->
                            <b-row>
                                <b-col cols="4">
                                    <label for="job_name">Job name:</label>
                                </b-col>
                                <b-col cols="8">
                                    <b-form-input type="text" name="job_name" v-model='new_job.name' placeholder="job name..."></b-form-input>
                                </b-col>
                            </b-row>
                            <br>
                            <!-- Camera -->
                            <b-row>
                                <b-col cols="4">
                                    <label for="camera">Camera:</label>
                                </b-col>
                                <b-col cols="8">
                                    <b-form-select name="camera" v-model="new_job.camera" :options="['other', 'central', 'left', 'right']"></b-form-select>
                                </b-col>
                            </b-row>
                            <br>
                            <!-- Upload files -->
                            <b-row>
                                <b-col cols="4">
                                    <label>Files:</label>
                                </b-col>
                                <b-col cols="8">
                                    <b-row>
                                        <b-col cols="12">
                                            <!-- Type input -->
                                            <b-button-group size="sm" id="files_btn">
                                                <b-button class="toggle_btn" @click="new_job.type_input = 'files'; new_job.files = [];" variant="primary" :class="{'active': new_job.type_input == 'files'}">Files</b-button>
                                                <b-button class="toggle_btn" @click="new_job.type_input = 'video'; new_job.files = null;" variant="primary" :class="{'active': new_job.type_input == 'video'}">Video</b-button>
                                                <b-button class="toggle_btn" @click="new_job.type_input = 'zip'; new_job.files = null;" variant="primary" :class="{'active': new_job.type_input == 'zip'}">Zip</b-button>
                                                <b-button class="toggle_btn" @click="new_job.type_input = 'ftp'; new_job.files = null;" variant="primary" :class="{'active': new_job.type_input == 'ftp'}">FTP</b-button>
                                                <b-button class="toggle_btn" @click="new_job.type_input = 'corpus'; new_job.files = null;" variant="primary" :class="{'active': new_job.type_input == 'corpus'}">Corpus</b-button>
                                            </b-button-group>
                                            <!--<br><br>
                                                <b-button-group size="sm" id="files_btn" v-if="this.new_job.type_input == 'files'">
                                                    <b-button class="toggle_btn" @click="new_job.type_files = 'use_files'" variant="primary" :class="{'active': this.new_job.type_files == 'use_files'}">use files</b-button>
                                                    <b-button class="toggle_btn" @click="new_job.type_files = 'use_folder'" variant="primary" :class="{'active': this.new_job.type_files == 'use_folder'}">use folder</b-button> 
                                                </b-button-group>-->
                                        </b-col>
                                    </b-row>
                                    <br>
                                    <b-row>
                                        <!-- Files -->
                                        <b-col cols="12" v-if="new_job.type_input == 'files'">
                                            <b-form-file @input="" id="file_uploader" v-model='new_job.files' accept="image/*,.xml" multiple no-drop placeholder="files...">
                                                <template slot="file-name" slot-scope="{ names }">
                                                    <b-badge variant="dark">{{ names[0] }}</b-badge>
                                                    <b-badge v-if="names.length > 1" variant="dark" class="ml-1">
                                                        + {{ names.length - 1 }} More files
                                                    </b-badge>
                                                </template>
                                            </b-form-file>
                                            <b-row class="mb-2">
                                                <b-col>
                                                    <b-form-checkbox
                                                        v-if="!has_autolabel_sport(new_job.sport)"
                                                        id="enable_autolabeling_checkbox"
                                                        v-model="new_job.files_params.files.enable_autolabeling"
                                                        name="enable_autolabeling_checkbox"
                                                        :value="true"
                                                        :unchecked-value="false"
                                                        >
                                                        Enable autolabeling
                                                    </b-form-checkbox>
                                                </b-col>
                                            </b-row>
                                            <b-row class="mb-2">
                                                <b-col>
                                                    <b-form-checkbox
                                                        id="each_file_one_job"
                                                        v-model="new_job.files_params.files.each_file_one_job"
                                                        name="each_file_one_job"
                                                        :value="true"
                                                        :unchecked-value="false"
                                                        >
                                                        Each file one individual job
                                                    </b-form-checkbox>
                                                </b-col>
                                            </b-row>

                                            <v-icon name="info" style="width: 20px"></v-icon>
                                            if the number of files is more than 1,000 files, use other option.
                                        </b-col>

                                        <!-- Video -->
                                        <b-col cols="12" style="padding-left: 0; margin-left: 0;" v-if="new_job.type_input == 'video'">
                                            <b-form-file @input="get_video_duration" id="file_uploader" v-model='new_job.files' accept="video/*" no-drop placeholder="video..."></b-form-file>
                                            <!-- Optionals video -->
                                            <br><br>
                                            <div v-if="new_job.files != null && !Array.isArray(new_job.files)">
                                                <b-row class="mb-2">
                                                    <b-col>
                                                        <b-form-checkbox
                                                            v-if="!has_autolabel_sport(new_job.sport)"
                                                            id="enable_autolabeling_checkbox"
                                                            v-model="new_job.files_params.video.enable_autolabeling"
                                                            name="enable_autolabeling_checkbox"
                                                            :value="true"
                                                            :unchecked-value="false"
                                                            >
                                                            Enable autolabeling
                                                        </b-form-checkbox>
                                                    </b-col>
                                                </b-row>
                                                <b-row class="mb-2">
                                                    <b-col sm="6" class="text-sm-left"><b><small>Start:</small></b></b-col>
                                                    <b-col>
                                                        <timeselector :utc="true" :interval="{h:1, m:1, s:1}" :displayHours="true" :displayMinutes="true" :displaySeconds="true" v-model="new_job.files_params.video.start_time"></timeselector>
                                                    </b-col>
                                                </b-row>
                                                <b-row class="mb-2">
                                                    <b-col sm="6" class="text-sm-left"><b><small>Duration:</small></b></b-col>
                                                    <b-col>
                                                        <timeselector :utc="true" :interval="{h:1, m:1, s:1}" :displayHours="true" :displayMinutes="true" :displaySeconds="true" v-model="new_job.files_params.video.duration"></timeselector>
                                                    </b-col>
                                                </b-row>
                                                <b-row class="mb-2">
                                                    <b-col sm="6" class="text-sm-left"><b><small>Sampling Period:</small></b></b-col>
                                                    <b-col>
                                                        <timeselector :utc="true" :interval="{h:1, m:1, s:1}" :displayHours="false" :displayMinutes="true" :displaySeconds="true" v-model="new_job.files_params.video.every"></timeselector>
                                                    </b-col>
                                                </b-row>
                                            </div>
                                            <v-icon name="info" style="width: 20px"></v-icon>
                                            can only contain the same match.
                                        </b-col>

                                        <!-- Zip -->
                                        <b-col cols="12" style="padding-left: 0; margin-left: 0;" v-if="new_job.type_input == 'zip'">
                                            <b-row>
                                                <b-col>
                                                    <b-form-file @input="" id="file_uploader" v-model='new_job.files' accept="application/x-bzip, application/x-bzip2, application/x-rar-compressed, application/x-tar, application/zip, application/x-7z-compressed" no-drop placeholder="zip..."></b-form-file>
                                                </b-col>
                                            </b-row>
                                            <b-row class="mb-2">
                                                <b-col>
                                                    <b-form-checkbox
                                                        v-if="!has_autolabel_sport(new_job.sport)"
                                                        id="enable_autolabeling_checkbox"
                                                        v-model="new_job.files_params.zip.enable_autolabeling"
                                                        name="enable_autolabeling_checkbox"
                                                        :value="true"
                                                        :unchecked-value="false"
                                                        >
                                                        Enable autolabeling
                                                    </b-form-checkbox>
                                                </b-col>
                                            </b-row>
                                            <b-row class="mb-2">
                                                <b-col>
                                                    <b-form-checkbox
                                                        id="each_file_one_job"
                                                        v-model="new_job.files_params.zip.each_file_one_job"
                                                        name="each_file_one_job"
                                                        :value="true"
                                                        :unchecked-value="false"
                                                        >
                                                        Each file one individual job
                                                    </b-form-checkbox>
                                                </b-col>
                                            </b-row>

                                            <b-row class="mb-2">
                                                <b-col sm="4" class="text-sm-right"><b><small>Annotation every:</small></b></b-col>
                                                <b-col>
                                                    <timeselector :utc="true" :interval="{h:1, m:1, s:1}" :displayHours="false" :displayMinutes="true" :displaySeconds="true" v-model="new_job.files_params.zip.every"></timeselector>
                                                </b-col>
                                            </b-row>
                                            <v-icon name="info" style="width: 20px"></v-icon>
                                            if zip contains videos.
                                        </b-col>

                                        <!-- FTP -->
                                        <b-col cols="12" style="padding-left: 0; margin-left: 0;" v-if="new_job.type_input == 'ftp'">
                                            <b-row>
                                                <b-col>
                                                    <b-row class="mb-2">
                                                        <b-col>
                                                            <b-form-checkbox
                                                                v-if="!has_autolabel_sport(new_job.sport)"
                                                                id="enable_autolabeling_checkbox"
                                                                v-model="new_job.files_params.ftp.enable_autolabeling"
                                                                name="enable_autolabeling_checkbox"
                                                                :value="true"
                                                                :unchecked-value="false"
                                                                >
                                                                Enable autolabeling
                                                            </b-form-checkbox>
                                                        </b-col>
                                                    </b-row>
                                                    <b-button variant="primary" @click="this.do_ftp_credentials" v-if="!new_job.files_params.ftp.loading && new_job.files_params.ftp.username == null">
                                                        Get FTP credentials
                                                    </b-button>
                                                    <div v-if="new_job.files_params.ftp.username != null">
                                                        <b-row class="mb-2">
                                                            <b-col sm="4" class="text-sm-right"><b>Host:</b></b-col>
                                                            <b-col>{{ new_job.files_params.ftp.host }}</b-col>
                                                        </b-row>
                                                        <b-row class="mb-2">
                                                            <b-col sm="4" class="text-sm-right"><b>Port:</b></b-col>
                                                            <b-col>{{ new_job.files_params.ftp.port }}</b-col>
                                                        </b-row>
                                                        <b-row class="mb-2">
                                                            <b-col sm="4" class="text-sm-right"><b>Username:</b></b-col>
                                                            <b-col>{{ new_job.files_params.ftp.username }}</b-col>
                                                        </b-row>
                                                        <b-row class="mb-2">
                                                            <b-col sm="4" class="text-sm-right"><b>Password:</b></b-col>
                                                            <b-col>{{ new_job.files_params.ftp.password }}</b-col>
                                                        </b-row>
                                                        <b-row class="mb-2">
                                                            <b-col sm="4" class="text-sm-right"><b>This FTP config will expire in :</b></b-col>
                                                            <b-col>{{ second_to_time(new_job.files_params.ftp.expiration) }}</b-col>
                                                        </b-row>
                                                    </div>
                                                </b-col>
                                            </b-row>

                                            <b-row class="mb-2">
                                                <b-col>
                                                    <b-form-checkbox
                                                        id="each_file_one_job"
                                                        v-model="new_job.files_params.ftp.each_file_one_job"
                                                        name="each_file_one_job"
                                                        :value="true"
                                                        :unchecked-value="false"
                                                        >
                                                        Each file one individual job
                                                    </b-form-checkbox>
                                                </b-col>
                                            </b-row>

                                            <b-row class="mb-2">
                                                <b-col sm="4" class="text-sm-right"><b><small>Annotation every:</small></b></b-col>
                                                <b-col>
                                                    <timeselector :utc="true" :interval="{h:1, m:1, s:1}" :displayHours="false" :displayMinutes="true" :displaySeconds="true" v-model="new_job.files_params.ftp.every"></timeselector>
                                                </b-col>
                                            </b-row>
                                            <v-icon name="info" style="width: 20px"></v-icon>
                                            if FTP contains videos
                                        </b-col>

                                        <!-- CORPUS -->
                                        <b-col cols="12" style="padding-left: 0; margin-left: 0;" v-if="new_job.type_input == 'corpus'">
                                            <b-col>
                                                <b-row class="mb-2">
                                                    <b-col>
                                                        <b-row>
                                                            <b-col cols="3">
                                                                <label for="corpus_route">Glob route:</label>
                                                            </b-col>
                                                            <b-col cols="9">
                                                                <b-form-input type="text" name="corpus_route" v-model='new_job.files_params.corpus.glob_route' placeholder="route..."></b-form-input>
                                                            </b-col>
                                                        </b-row>

                                                        <v-icon name="info" style="width: 20px"></v-icon>
                                                        Use relative path with respect to <b>corpus/</b> because this path can be different on each computer.
                                                    </b-col>
                                                </b-row>

                                                <b-row class="mb-2">
                                                    <b-col>
                                                        <b-form-checkbox
                                                            id="each_file_one_job"
                                                            v-model="new_job.files_params.corpus.each_file_one_job"
                                                            name="each_file_one_job"
                                                            :value="true"
                                                            :unchecked-value="false"
                                                            >
                                                            Each file one individual job
                                                        </b-form-checkbox>
                                                    </b-col>
                                                </b-row>
                                                <b-row class="mb-2">
                                                    <b-col sm="6" class="text-sm-left"><b><small>Start:</small></b></b-col>
                                                    <b-col>
                                                        <timeselector :utc="true" :interval="{h:1, m:1, s:1}" :displayHours="true" :displayMinutes="true" :displaySeconds="true" v-model="new_job.files_params.corpus.start_time"></timeselector>
                                                    </b-col>
                                                </b-row>
                                                <b-row class="mb-2">
                                                    <b-col sm="6" class="text-sm-left"><b><small>Duration:</small></b></b-col>
                                                    <b-col>
                                                        <timeselector :utc="true" :interval="{h:1, m:1, s:1}" :displayHours="true" :displayMinutes="true" :displaySeconds="true" v-model="new_job.files_params.corpus.duration"></timeselector>
                                                    </b-col>
                                                </b-row>
                                                <b-row class="mb-2">
                                                    <b-col sm="6" class="text-sm-left"><b><small>Sampling Period:</small></b></b-col>
                                                    <b-col>
                                                        <timeselector :utc="true" :interval="{h:1, m:1, s:1}" :displayHours="false" :displayMinutes="true" :displaySeconds="true" v-model="new_job.files_params.corpus.every"></timeselector>
                                                    </b-col>
                                                </b-row>
                                                <v-icon name="info" style="width: 20px"></v-icon>
                                                <!-- if CORPUS contains videos -->
                                                if CORPUS contains videos
                                            </b-col>
                                        </b-col>

                                        <!-- EOF TYPES -->
                                    </b-row>
                                </b-col>
                            </b-row>
                            <br>
                            <!-- Files props -->
                            <b-row>
                                <b-col cols="4">
                                    <label for="job_order">File ordering:</label>
                                </b-col>
                                <b-col cols="8">
                                    <b-form-select name="sport" v-model="new_job.order" :options="preferences.file_order"></b-form-select>
                                    <div v-if="new_job.order == 'CUSTOM (regex by name)'">
                                        <b-form-input type="text" name="job_regex" v-model='new_job.order_regex' placeholder="regex order..."></b-form-input>
                                        <br>
                                        <v-icon name="info" style="width: 20px"></v-icon>
                                        <b-button :pressed.sync="new_job.order_show_details" variant="primary" size="sm" >Show details</b-button>

                                        <br>
                                        <br>
                                        <div v-if="new_job.order_show_details">
                                            The RegEx ordering system is based only on the basename of the file (not the path). <b>The files that not match with the expression will not be included</b>.
                                            <br>To simplify the expressions, have been changed to: 
                                            <br><b>{("string"|"number"|"float"):("asc"|"desc"):order_index}</b> where "<b>:</b>" is used to split information. 
                                            <br>The <b>first value</b> represents the nature of the data that we capture, the <b>second value</b> is optional and represents the ordering asc for ASCENDING, desc for DESCENDING (for default is ASCENDING) and the <b>last value</b> is the index of priority order_index.
                                            <br>The order is evaluated by the index order as a <b>hierarchical ordering</b>. 
                                            <br>
                                            <br><b>The possibles data types</b>: string, number, float.
                                            <br><b>The possibles order types</b>: asc, desc.
                                            <br>
                                            <br><b>For instance</b>: <b>{string:desc:0}_{number:asc:1}.jpg</b> for the files <b>["adeu_2.jpg", "adeu_1.jpg", "hola_1.jpg"]</b>
                                            <ol type="1">
                                                <li>First order the <b>{string:desc:0}</b> because have the lower order index. The order is DESCENDING. <br>
                                                    <b>["hola_1.jpg", "adeu_2.jpg", "adeu_1.jpg"]</b>
                                                </li>
                                                <li>Second order the <b>{number:asc:1}</b> because have the next lower order index. The order is ASCENDING. <br>
                                                    <b>["hola_1.jpg", "adeu_1.jpg", "adeu_2.jpg"]</b>
                                                </li>
                                                <li>
                                                    Repeat the process until there are not more indices to order.
                                                </li>
                                            </ol> 
                                        </div>

                                    </div>
                                </b-col>
                            </b-row>
                            <br>

                            <!-- Label ROI? -->
                            <b-row>
                                <b-col cols="4">
                                    <label for="priority">Label the ROI of the field:</label>
                                </b-col>
                                <b-col cols="8">
                                    <b-form-checkbox
                                        id="label_roi"
                                        v-model="new_job.label_roi"
                                        name="label_roi"
                                        :value="true"
                                        :unchecked-value="false"
                                        >
                                        Enable/Disable
                                    </b-form-checkbox>
                                </b-col>
                            </b-row>
                            

                            <!-- Priority -->
                            <b-row>
                                <b-col cols="4">
                                    <label for="priority">Priority:</label>
                                </b-col>
                                <b-col cols="8">
                                    <b-row>
                                        <b-col cols="10">
                                            <b-form-input type="range" name="priority" min="0" max="10" v-model="new_job.priority"></b-form-input>
                                        </b-col>
                                        <b-col cols="2">
                                            <span>{{ new_job.priority }}</span>
                                        </b-col>
                                    </b-row>
                                </b-col>
                            </b-row>
                            <br>
                            <!-- Sports -->
                            <b-row>
                                <b-col cols="4">
                                    <label for="sport">Sport:</label>
                                </b-col>
                                <b-col>
                                    <b-row>
                                        <b-form-select name="sport" v-model="new_job.sport" :options="preferences.sports_list"></b-form-select>
                                        <span v-if="!has_autolabel_sport(new_job.sport)">
                                            <v-icon name="info" style="width: 20px"></v-icon>
                                            This sport not have autolabeling model 
                                        </span>
                                    </b-row>
                                </b-col>
                            </b-row>
                            <br>
                            <!-- Tags -->
                            <b-row>
                                <b-col cols="4">
                                    <label for="tags">Job Tags:</label>
                                </b-col>
                                <b-col>
                                    <b-row>
                                        <b-button size="sm" @click="do_toggle_tag($event, null, new_job.tags, tag)" class="toggle_btn" v-for="(tag, idx) in expanded_tags_list(new_job.sport)" :class="{active: new_job.tags.includes(tag)}" variant="primary">
                                            {{ tag }}
                                        </b-button>
                                    </b-row>
                                </b-col>
                            </b-row>
                            <br>
                            <!-- Frame Tags -->
                            <b-row>
                                <b-col cols="4">
                                    <label for="tags">Frame Tags:</label>
                                </b-col>
                                <b-col>
                                    <b-row>
                                        <b-button size="sm" @click="do_toggle_frame_tag($event, null, new_job.frame_tags, frame_tag)" class="toggle_btn" v-for="(frame_tag, idx) in expanded_frame_tags_list(new_job.sport)" :class="{active: new_job.frame_tags.includes(frame_tag)}" variant="primary">
                                            {{ frame_tag }}
                                        </b-button>
                                    </b-row>
                                </b-col>
                            </b-row>

                            <!-- Comments -->
                            <b-row>
                                <b-col>
                                    <label for="job_comments">Comments:</label>
                                </b-col>
                            </b-row>
                            <b-row>
                                <b-col>
                                    <b-form-textarea
                                      id="job_comments"
                                      v-model="new_job.comments"
                                      placeholder="Additional comments..."
                                      rows="5"
                                      max-rows="6"
                                    ></b-form-textarea>
                                </b-col>
                            </b-row>
                            <br>

                        </b-form-group>
                        <br><br>
                        <b-button style="float: right;" @click="do_create_job" variant="primary">Create</b-button>
                        <div v-if="this.new_job.message != ''">
                            <span style="color: #f00;">{{ this.new_job.message }}</span>
                        </div>
                    </b-card>
                    <br>
                    <!-- Configs -->
                    <b-card bg-variant="light">
                        <b-form-group
                            label="Main Configs"
                            label-size="lg"
                            label-align-sm="top"
                            label-class="font-weight-bold pt-0"
                            class="mb-0"
                            >
                            <b-row>
                                <b-col>
                                    <!-- Sports -->
                                    <b-row>
                                        <b-col cols="4">
                                            <label for="sport">Sport:</label>
                                        </b-col>
                                        <b-col cols="6">
                                            <b-row>
                                                <b-form-select name="sport" v-model="config.selected_sport" :options="preferences_expanded_sport_list"></b-form-select>
                                            </b-row>
                                        </b-col>
                                        <b-col>
                                            <b-button size="sm" v-if="config.selected_sport != null && config.selected_sport != config.not_selected_sport" v-b-modal="'remove-sport'">-</b-button>
                                            <b-button size="sm" style="margin-left: 10px;" v-b-modal="'add-sport'">+</b-button>
                                            <b-modal @ok="do_new_sport" id="add-sport">
                                                <label for="new_sport">New sport:</label>
                                                <b-form-input type="text" name="new_sport" v-model='config.new_sport' placeholder="new sport..."></b-form-input>
                                            </b-modal>
                                            <b-modal @ok="do_remove_sport" id="remove-sport">
                                                Do you want to delete {{ config.selected_sport  }}?
                                            </b-modal>
                                        </b-col>
                                    </b-row>
                                    <br>
                                    <!-- Job Tags -->
                                    <b-row>
                                        <b-col cols="4">
                                            <label for="tags" v-if="config.selected_sport == null || config.selected_sport == config.not_selected_sport">Job Generic Tags:</label>
                                            <label for="tags" v-else style="text-transform: capitalize;">Job {{ config.selected_sport }} Tags:</label>
                                        </b-col>
                                        <b-col cols="6">
                                            <b-row>
                                                <b-button size="sm" class="toggle_btn" v-for="(tag, idx) in expanded_config_tags_list(config.selected_sport)" variant="primary">
                                                    {{ tag }} <span @click="prepare_remove_tag($event, tag)">(x)</span>
                                                </b-button>
                                            </b-row>
                                        </b-col>
                                        <b-col>
                                            <b-button size="sm" v-b-modal="'add-tag'">+</b-button>
                                            <b-modal @ok="do_new_tag" id="add-tag">
                                                <span v-if="config.selected_sport != null && config.selected_sport != config.not_selected_sport">
                                                Selected sport: <b>{{ config.selected_sport }}</b>
                                                <br>
                                                </span>
                                                <label for="new_tag">New job tag:</label>
                                                <b-form-input type="text" name="new_tag" v-model='config.new_tag' placeholder="new tag..."></b-form-input>
                                            </b-modal>
                                            <b-modal @ok="do_remove_tag" id="remove-tag">
                                                <span v-if="config.selected_sport != null && config.selected_sport != config.not_selected_sport">
                                                Do you want to delete {{ config.aux_remove_tag }} tag for {{ config.selected_sport }} sport?
                                                </span>
                                                <span v-else>
                                                Do you want to delete {{ config.aux_remove_tag }} tag?
                                                </span>
                                            </b-modal>
                                        </b-col>
                                    </b-row>
                                    <!-- Frame Tags -->
                                    <b-row>
                                        <b-col cols="4">
                                            <label for="frame_tags" v-if="config.selected_sport == null || config.selected_sport == config.not_selected_sport">Frame Generic Tags:</label>
                                            <label for="frame_tags" v-else style="text-transform: capitalize;">Frame {{ config.selected_sport }} Tags:</label>
                                        </b-col>
                                        <b-col cols="6">
                                            <b-row>
                                                <b-button size="sm" class="toggle_btn" v-for="(tag, idx) in expanded_config_frame_tags_list(config.selected_sport)" variant="primary">
                                                    {{ tag }} <span @click="prepare_remove_frame_tag($event, tag)">(x)</span>
                                                </b-button>
                                            </b-row>
                                        </b-col>
                                        <b-col>
                                            <b-button size="sm" v-b-modal="'add-frame-tag'">+</b-button>
                                            <b-modal @ok="do_new_frame_tag" id="add-frame-tag">
                                                <span v-if="config.selected_sport != null && config.selected_sport != config.not_selected_sport">
                                                Selected sport: <b>{{ config.selected_sport }}</b>
                                                <br>
                                                </span>
                                                <label for="new_tag">New frame tag:</label>
                                                <b-form-input type="text" name="new_tag" v-model='config.new_frame_tag' placeholder="new tag..."></b-form-input>
                                            </b-modal>
                                            <b-modal @ok="do_remove_frame_tag" id="remove-frame-tag">
                                                <span v-if="config.selected_sport != null && config.selected_sport != config.not_selected_sport">
                                                Do you want to delete {{ config.aux_remove_frame_tag }} frame tag for {{ config.selected_sport }} sport?
                                                </span>
                                                <span v-else>
                                                Do you want to delete {{ config.aux_remove_frame_tag }} frame tag?
                                                </span>
                                            </b-modal>
                                        </b-col>
                                    </b-row>
                                </b-col>
                            </b-row>
                        </b-form-group>
                    </b-card>
                </b-col>
                <!-- MIDDLE COLUMN -->
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
                                @row-clicked="showDetailsRow"
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
                                }, 
                                { 
                                key: 'has_errors', 
                                label: 'Valid',
                                sortable: true,
                                formatter(value, key, item){
                                return item.files_error !== undefined;
                                },
                                sortable: true,
                                }, 
                                { 
                                key: 'show_details', 
                                label: 'Show',
                                }, 
                                { 
                                key: 'view_metrics', 
                                label: 'Metrics',
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
                                <template v-slot:cell(show_details)="row">
                                    <b-button size="sm" @click="showDetailsRow(row.item)" class="mr-2">
                                        {{ row.detailsShowing ? 'Hide' : 'Show'}} Details
                                    </b-button>
                                </template>
                                <template v-slot:cell(view_metrics)="row">
                                    <b-button v-if="row.item.status >= preferences.status_list.indexOf('IN_PROCESS')" size="sm" class="mr-2"><a style="color: #fff !important;" :href="'/#/metrics/' + row.item._id.$oid" target="_blank">View</a></b-button>
                                </template>
                                <template v-slot:cell(eye)="row">
                                    <v-icon name="eye" v-if="row.item.visible" style="width: 20px"></v-icon>
                                    <v-icon name="eye-off" v-else style="width: 20px"></v-icon>
                                </template>
                                <template v-slot:cell(has_errors)="row">
                                    <v-icon name="flag" v-if="row.item.files_error !== undefined" style="width: 20px"></v-icon>
                                    <v-icon name="check" v-else style="width: 20px"></v-icon>
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
                                <template v-slot:row-details="row">
                                    <div :class="{cancel: row.item.cancel != undefined && row.item.cancel}" style="position: relative;">
                                        <div style="position: absolute; right: 0; top: 0; z-index: 999;">
                                            <b-button @click="do_list_jobs" size="sm" style="border-bottom-right-radius: 0 !important; border-top-left-radius: 0 !important;">
                                                Refresh
                                            </b-button>
                                        </div>
                                        <b-card>
                                            <b-row class="mb-2">
                                                <b-col sm="3" class="text-sm-right"><b>Name:</b></b-col>
                                                <b-col>{{ row.item.name }}</b-col>
                                            </b-row>
                                            <b-row class="mb-2">
                                                <b-col sm="3" class="text-sm-right"><b>Camera:</b></b-col>
                                                <b-col>{{ row.item.camera }}</b-col>
                                            </b-row>
                                            <b-row class="mb-2">
                                                <b-col sm="3" class="text-sm-right"><b>Created by:</b></b-col>
                                                <b-col>{{ row.item.created_by_name }}</b-col>
                                            </b-row>
                                            <b-row class="mb-2" v-if="row.item.cancel != undefined && row.item.cancel" style="border-color: #f00;">
                                                <b-col sm="3" class="text-sm-right"><b>Cancelled at:</b></b-col>
                                                <b-col>{{ date_to_str(row.item.cancelled_at) }}</b-col>
                                            </b-row>
                                            <b-row class="mb-2">
                                                <b-col sm="3" class="text-sm-right"><b>Priority:</b></b-col>
                                                <b-col>{{ row.item.priority }}</b-col>
                                            </b-row>
                                            <b-row class="mb-2">
                                                <b-col sm="3" class="text-sm-right"><b>Status:</b></b-col>
                                                <b-col>
                                                    <b-button style="cursor: default;" size="sm" variant="primary" :class="{['status_' + preferences.status_list[row.item.status]]: true}">{{ preferences.status_list[row.item.status] }}</b-button>
                                                </b-col>
                                            </b-row>
                                            <b-row class="mb-2">
                                                <b-col sm="3" class="text-sm-right"><b>Sport:</b></b-col>
                                                <b-col>{{ row.item.sport }}</b-col>
                                            </b-row>
                                            <b-row class="mb-2">
                                                <b-col sm="3" class="text-sm-right"><b>Status historic:</b></b-col>
                                                <b-col style="padding: 20px; background-color: #ccc">
                                                    <b-row class="mb-2">
                                                        <b-col sm="5" class="text-sm-right"><b>Created:</b></b-col>
                                                        <b-col>{{ date_to_str(row.item.created_at) }}</b-col>
                                                    </b-row>
                                                    <b-row class="mb-2">
                                                        <b-col sm="5" class="text-sm-right"><b>Preprocess:</b></b-col>
                                                        <b-col>{{ date_to_str(row.item.preprocess_at) }} ({{ row.item.preprocess_step }} / {{ preferences.total_preprocess_steps }})</b-col>
                                                        <b-col><b>Name:</b> <span style="text-transform: capitalize;">{{ row.item.preprocess_name }}</span></b-col>
                                                    </b-row>
                                                    <b-row class="mb-2">
                                                        <b-col sm="5" class="text-sm-right"><b>Labeling:</b></b-col>
                                                        <b-col>{{ date_to_str(row.item.labeling_at) }}</b-col>
                                                    </b-row>
                                                    <b-row class="mb-2">
                                                        <b-col sm="5" class="text-sm-right"><b>Finished:</b></b-col>
                                                        <b-col>{{ date_to_str(row.item.finished_at) }} ({{ row.item.postprocess_step }} / {{ preferences.total_postprocess_steps }})</b-col>
                                                        <b-col><b>Name:</b> <span v-if="row.item.labeling_at !== undefined && row.item.labeling_at['$date'] !== undefined" style="text-transform: capitalize;">{{ row.item.postprocess_name }}</span><span v-else style="text-transform: capitalize;">-</span></b-col>
                                                    </b-row>
                                                </b-col>
                                            </b-row>
                                            <b-row class="mb-2">
                                                <b-col sm="3" class="text-sm-right"><b>Trace:</b></b-col>
                                                <b-col style="padding: 20px; background-color: #ccc">
                                                    <b-row class="mb-2" v-for="(item_process, key_process) in row.item.trace" :key="key_process" v-if="row.item.trace != null && row.item.trace != undefined">
                                                        <b-col sm="4" class="text-sm-right" style="text-transform: capitalize;"><b>{{key_process}}:</b></b-col>
                                                        <b-col>
                                                            <b-row class="mb-2" v-for="(item_step, key_step) in item_process" :key="key_step" v-if="item_process != null && item_process != undefined">
                                                                <b-col sm="8" class="text-sm-right" style="text-transform: capitalize;"><b><small>{{key_step}}:</small></b></b-col>
                                                                <b-col>{{ Math.round(item_step) }}%</b-col>
                                                            </b-row>
                                                        </b-col>
                                                    </b-row>
                                                </b-col>
                                            </b-row>
                                            <b-row class="mb-2">
                                                <b-col sm="3" class="text-sm-right"><b>Done files:</b></b-col>
                                                <b-col>{{ row.item.done_files }}</b-col>
                                            </b-row>
                                            <b-row class="mb-2">
                                                <b-col sm="3" class="text-sm-right"><b>Total files:</b></b-col>
                                                <b-col>{{ row.item.total_files }}</b-col>
                                            </b-row>
                                            <b-row class="mb-2">
                                                <b-col sm="3" class="text-sm-right"><b>Visibility:</b></b-col>
                                                <b-col>
                                                    {{ row.item.visible }} 
                                                    <b-button @click="do_change_visibility(row.item, true)" v-if="!row.item.visible" size="sm" variant="primary">Show</b-button>
                                                    <b-button @click="do_change_visibility(row.item, false)" v-if="row.item.visible" size="sm" variant="secondary">Hide</b-button>
                                                </b-col>
                                            </b-row>
                                            <b-row class="mb-2">
                                                <b-col sm="3" class="text-sm-right"><b>Generic Tags:</b></b-col>
                                                <b-col>
                                                    <b-row>
                                                        <b-button size="sm" @click="do_toggle_tag($event, row.item, row.item.tags, tag)" class="toggle_btn" v-for="(tag, idx) in expanded_tags_list(row.item.sport)" :class="{active: row.item.tags.includes(tag)}" variant="primary">
                                                            {{ tag }}
                                                        </b-button>
                                                    </b-row>
                                                </b-col>
                                            </b-row>
                                            <b-row class="mb-2">
                                                <b-col sm="3" class="text-sm-right"><b>Frame Tags:</b></b-col>
                                                <b-col>
                                                    <b-row>
                                                        <b-button size="sm" @click="do_toggle_frame_tag($event, row.item, row.item.frame_tags, frame_tag)" class="toggle_btn" v-for="(frame_tag, idx) in expanded_frame_tags_list(row.item.sport)" :class="{active: row.item.frame_tags.includes(frame_tag)}" variant="primary">
                                                            {{ frame_tag }}
                                                        </b-button>
                                                    </b-row>
                                                </b-col>
                                            </b-row>
                                            <b-row class="mb-2" v-if="row.item.files_error != undefined">
                                                <b-col sm="3" class="text-sm-right"><b>Errors:</b></b-col>
                                                <b-col style="padding: 20px; background-color: #ccc; height: 200px; overflow-y: scroll;">
                                                    <div v-for="(f, index) in row.item.files_error">
                                                        <b-row>
                                                            <b-col class="text-sm-right"><b>{{f.path}}:</b></b-col>
                                                        </b-row>
                                                        <b-row>
                                                            <b-col>{{ f.message }}</b-col>
                                                        </b-row>
                                                    </div>
                                                </b-col>
                                            </b-row>

                                            <b-row class="mb-2" v-if="row.item.alerts != undefined">
                                                <b-col sm="3" class="text-sm-right"><b>Alerts:</b></b-col>
                                                <b-col style="padding: 20px; background-color: #ccc; height: 200px; overflow-y: scroll;">
                                                    <div v-for="(m, index) in row.item.alerts">
                                                        <b-row>
                                                            <b-col>{{ m }}</b-col>
                                                        </b-row>
                                                    </div>
                                                </b-col>
                                            </b-row>

                                            <b-row class="mb-2">
                                                <b-col sm="3" class="text-sm-right"><b>Comments:</b></b-col>
                                                <b-col>
                                                    <b-row>
                                                        <textarea class="comments form-control" disabled style="width: 100%">{{ row.item.comments }}</textarea>
                                                    </b-row>
                                                </b-col>
                                            </b-row>

                                            <b-row class="mb-2">
                                                <b-col sm="3" class="text-sm-right"><b>Remove:</b></b-col>
                                                <b-col>
                                                    <b-row>
                                                        <b-button style="margin-left: 10px;" size="sm" @click="remove_job($event, row.item, false)" variant="danger">
                                                            <span v-if="row.item.variables != null && row.item.variables.parent_id != null && row.item.variables !== undefined && row.item.variables.parent_id !== undefined">
                                                                Remove unique job
                                                            </span>
                                                            <span v-else>
                                                                Remove job
                                                            </span>
                                                        </b-button>
                                                        <b-button style="margin-left: 10px;" v-if="preferences.status_list[row.item.status] == 'FINISHED'" size="sm" @click="remove_job($event, row.item, true)" variant="danger">
                                                            <span v-if="row.item.variables != null && row.item.variables.parent_id != null && row.item.variables !== undefined && row.item.variables.parent_id !== undefined">
                                                                Remove unique job <b>including output files</b>
                                                            </span>
                                                            <span v-else>
                                                                Remove job <b>including output files</b>
                                                            </span>
                                                        </b-button>

                                                        <b-button style="margin-left: 10px;" v-if="row.item.variables != null && row.item.variables.parent_id != null && row.item.variables !== undefined && row.item.variables.parent_id !== undefined" size="sm" @click="remove_entire_job($event, row.item, false)" variant="danger">
                                                            Remove full job
                                                        </b-button>
                                                        <b-button v-if="row.item.variables != null && row.item.variables.parent_id != null && row.item.variables !== undefined && row.item.variables.parent_id !== undefined && preferences.status_list[row.item.status] == 'FINISHED'" style="margin-left: 10px;" size="sm" @click="remove_entire_job($event, row.item, true)" variant="danger">
                                                            Remove full job <b>including output files</b>
                                                        </b-button>
                                                    </b-row>
                                                </b-col>
                                            </b-row>
                                            <b-button style="float: right;" size="sm" @click="row.toggleDetails">Hide Details</b-button>
                                        </b-card>
                                    </div>
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
                <!-- BOTTOM COLUMN -->
                <!-- User Manager -->
                <b-col cols="3">
                    <b-card bg-variant="light">
                        <b-form-group
                            label="User Manager"
                            label-size="lg"
                            label-align-sm="top"
                            label-class="font-weight-bold pt-0"
                            class="mb-0"
                            >
                            <div v-if="create_user.step == 'create'">
                                <b-row class="mb-2">
                                    <b-col sm="5" class="text-sm-right"><b>Username:</b></b-col>
                                    <b-col>
                                        <b-form-input name="create_user.username" v-model="create_user.username" placeholder="Enter your username"></b-form-input>
                                    </b-col>
                                </b-row>
                                <b-row class="mb-2">
                                    <b-col sm="5" class="text-sm-right"><b>Password:</b></b-col>
                                    <b-col>
                                        <b-form-input name="create_user.password" type="password" v-model="create_user.password" placeholder="Enter your password"></b-form-input>
                                    </b-col>
                                </b-row>
                                <b-row class="mb-2">
                                    <b-col sm="5" class="text-sm-right"><b>Group:</b></b-col>
                                    <b-col>
                                        <b-form-select v-model="create_user.selected_group" :options="preferences.groups_list" size="sm"></b-form-select>
                                    </b-col>
                                </b-row>
                                <b-button style="float: right; margin-left: 10px;" @click="do_list_users">Refresh</b-button>
                                <b-button style="float: right;" @click="do_create_user" variant="primary">Create</b-button>
                            </div>
                            <div v-if="create_user.step == 'message'">
                                {{ this.create_user.message }}
                                <br>
                                <b-button style="float: right;" @click="create_user.step = 'create'" variant="primary">Create other</b-button>
                            </div>
                            <br><br>
                            <b-table :items="list_users.users" :fields="['username', 'group', 'Active', {key: 'show_details', label: 'Show'}]" striped responsive="sm">
                                <template v-slot:cell(show_details)="row">
                                    <b-button size="sm" @click="row.toggleDetails" class="mr-2">
                                        {{ row.detailsShowing ? 'Hide' : 'Show'}} Details
                                    </b-button>
                                </template>
                                <template v-slot:cell(group)="row">
                                    {{ preferences.groups_list[row.item.group] }}
                                </template>
                                <template v-slot:cell(Active)="row">
                                    <div v-if="row.item.active != undefined && row.item.active != null && (new Date() - new Date(row.item.active['$date'])) < (1000 * 60 * 5)" class="active_btn yes"></div>
                                    <div v-else class="active_btn no"></div>
                                </template>
                                <template v-slot:row-details="row">
                                    <b-card>
                                        <b-row class="mb-2">
                                            <b-col sm="4" class="text-sm-right"><b>Username:</b></b-col>
                                            <b-col>{{ row.item.username }}</b-col>
                                        </b-row>
                                        <b-row class="mb-2">
                                            <b-col sm="4" class="text-sm-right"><b>Change password:</b></b-col>
                                            <b-col>
                                                <b-form-input type="password" v-model="change_user.password" placeholder=""></b-form-input>
                                                <br>
                                                <b-button style="float: right;" @click="do_change_user_password($event, row, row.item._id)">Change</b-button>
                                            </b-col>
                                        </b-row>

                                        <b-row class="mb-2">
                                            <b-col sm="4" class="text-sm-right"><b>Remove:</b></b-col>
                                            <b-col class="text-right">
                                                <b-row>
                                                    <b-button v-if="row.item.enable || row.item.enable === undefined" size="sm" @click="toggle_user($event, row.item, false)" variant="danger">
                                                        Disable user
                                                    </b-button>
                                                    <b-button v-else size="sm" @click="toggle_user($event, row.item, true)" variant="primary">
                                                        Enable user
                                                    </b-button>
                                                </b-row>
                                            </b-col>
                                        </b-row>

                                    </b-card>
                                </template>
                            </b-table>
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
                // New Job
                new_job: {
                    uuid: null,
                    name: '',
                    comments: '',
                    label_roi: true,
                    camera: 'other',
                    step: 'create',
                    priority: 5,
                    sport: null, //'none',
                    tags: [],
                    frame_tags: [],
                    files: [],
                    type_input: 'files',
                    //type_files: 'use_files',
                    resumable: null,
                    files_params: {
                        files: {
                            enable_autolabeling: true,
                            each_file_one_job: false,
                        },
                        video: {
                            enable_autolabeling: true,
                            start_time: new Date("1970-01-01T00:00:00Z"),
                            duration: null,
                            every: new Date("1970-01-01T00:00:01Z"),
                        },
                        zip: {
                            enable_autolabeling: true,
                            each_file_one_job: false,
                            every: new Date("1970-01-01T00:00:01Z"),
                        },
                        ftp: {
                            enable_autolabeling: true,
                            each_file_one_job: false,
                            loading: false,
                            username: null,
                            password: null,
                            token: null,
                            every: new Date("1970-01-01T00:00:01Z")
                        },

                        corpus: {
                            glob_route: null,
                            each_file_one_job: false,
                            start_time: new Date("1970-01-01T00:00:00Z"),
                            duration: null,
                            every: new Date("1970-01-01T00:00:01Z")
                        }
                    },
                    message: '',
                    step: 'create',
                    progress_bar: 0,
                    completed: false,
    
    
                    order: 'ASCEND BY MOD. DATE',
                    order_regex: null,
                    order_show_details: false
                },
    
                // List jobs
                list_jobs: {
                    sort_by: 'date',
                    sort_desc: true,
                    current_page: 1,
                    per_page: 10,
                    total: 0,
                    jobs: [],
                    selected_status: 'All',
                },
    
                // List users
                list_users: {
                    users: [],
                },
    
    
                // Create user
                create_user: {
                    step: 'create',
                    message: '',
                    username: '',
                    password: '',
                    selected_group: 'ADMIN',
                },
    
                // Change User
                change_user: {
                    password: '',
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
    
                config: {
                    new_tag: null,
                    aux_remove_tag: null,
    
                    new_frame_tag: null,
                    aux_remove_frame_tag: null,
    
                    new_sport: null,

                    selected_sport: 'All',
                    not_selected_sport: 'All'
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
    
                    file_order: ['ASCEND BY NAME', 'DESCEND BY NAME', 'ASCEND BY MOD. DATE', 'DESCEND BY MOD. DATE', 'CUSTOM (regex by name)']
                },     
            }
        },
    
        methods: {
            has_autolabel_sport(sport){
                let idx = this.preferences.sports_list.indexOf(this.new_job.sport);
                if(idx >= 0){
                    return this.preferences.sports_with_autolabeling_list[idx];
                }
                return true;
            },
    
            second_to_time(time){   
                // Hours, minutes and seconds
                let days = ~~(time / (3600 * 24));
                let hrs = ~~(time % (3600 * 24) / 3600);
                let mins = ~~((time % 3600) / 60);
                let secs = ~~time % 60;
    
                // Output like "1:01" or "4:03:59" or "123:03:59"
                let ret = days + " days and " + ("0" + hrs).slice(-2) + ":" + ("0" + mins).slice(-2) + ":" + ("0" + secs).slice(-2);
                return ret;
            },
    
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
                    self.list_users.users = response['data']['data']['users'];
                    self.preferences.total_preprocess_steps = response['data']['data']['total_preprocess_steps'];
                    self.preferences.total_postprocess_steps = response['data']['data']['total_postprocess_steps'];
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
                }else if(error.response['data']['error'] == 'Bad Request' && error.response['data']['description'] == 'Removed user'){
                    this.login.is_login = false;
                    this.login.message = 'Not allowed. User removed.';
                    this.$cookie.delete('token');
                }else if(error.response['data']['error'] == 'Bad Request' && error.response['data']['description'] == 'Invalid credentials'){
                    this.login.is_login = false;
                    this.login.message = 'Wrong username or password.';
                    this.$cookie.delete('token');
                }
            },
            get_video_duration(x){
                let self = this;
                let file_video = this.new_job.files;
    
                if(Array.isArray(file_video) || file_video == null){
                    return;
                }
                let video = document.createElement('video');
                video.preload = 'metadata';
    
                video.onloadedmetadata = function() {
                    window.URL.revokeObjectURL(video.src);
                    let t = new Date("1970-01-01T00:00:00Z");
                    t.setSeconds(video.duration);
                    if (self.new_job.type_input == 'video'){
                        self.new_job.files_params.video.duration = t;
                    }
                    else if(self.new_job.type_input == 'corpus'){
                        self.new_job.files_params.corpus.duration = t;
                    }
                }
    
                video.src = URL.createObjectURL(file_video);
            },
    
            showDetailsRow(row){
                for(let i = 0; i < this.$refs.jobs_table.items.length; i++){
                    if(row == this.$refs.jobs_table.items[i])
                        continue;
    
                    this.$set(this.$refs.jobs_table.items[i], '_showDetails', false);
                }
                this.$set(row, '_showDetails', !row._showDetails);
            },
    
            do_new_sport(bvModalEvt){
                let self = this;
                this.send_request({endpoint: Endpoints.PREFERENCES.SPORTS.ADD, method: 'POST', data: {
                    name: self.config.new_sport
                },
                on_response: function(response){
                    self.init_dashboard();
                    self.config.new_sport = null;
                },
    
                on_error: function(error){
                    self.login_error(error);
                    if(error.response['data']['error'] == 'error_add_sport'){
                        alert(error.response['data']['description']);
                    }
                }});
            },
    
            do_remove_sport(bvModalEvt){
                let self = this;
                this.send_request({endpoint: Endpoints.PREFERENCES.SPORTS.REMOVE, method: 'POST', data: {
                    name: self.config.selected_sport
                },
                on_response: function(response){
                    self.init_dashboard();
                    if(self.new_job.sport == self.config.selected_sport){
                        self.new_job.sport = null;
                    }
                    self.config.selected_sport = self.config.not_selected_sport;
                },
    
                on_error: function(error){
                    self.login_error(error);
                    if(error.response['data']['error'] == 'error_remove_sport'){
                        alert(error.response['data']['description']);
                    }
                }});
            },
    
            do_new_tag(bvModalEvt){
                let self = this;
    
                let selected_sport;
                if(this.config.selected_sport != null && this.config.selected_sport != this.config.not_selected_sport){
                    selected_sport = this.config.selected_sport;
                }else{
                    selected_sport = null;
                }
    
                this.send_request({endpoint: Endpoints.PREFERENCES.TAGS.ADD, method: 'POST', data: {
                    sport: selected_sport,
                    name: self.config.new_tag
                },
                on_response: function(response){
                    self.init_dashboard();
                    self.config.new_tag = null;
                },
    
                on_error: function(error){
                    self.login_error(error);
                    if(error.response['data']['error'] == 'error_tag_add'){
                        alert(error.response['data']['description']);
                    }
                }});
            },
    
            prepare_remove_tag(event, tag){
                event.preventDefault();
                event.stopPropagation();
    
                this.config.aux_remove_tag = tag;
                this.$bvModal.show('remove-tag');
    
            },
    
            do_remove_tag(bvModalEvt){
                if(this.config.aux_remove_tag == null)
                    return;
    
                let selected_sport;
                if(this.config.selected_sport != null && this.config.selected_sport != this.config.not_selected_sport){
                    selected_sport = this.config.selected_sport;
                }else{
                    selected_sport = null;
                }
    
                let self = this;
                this.send_request({endpoint: Endpoints.PREFERENCES.TAGS.REMOVE, method: 'POST', data: {
                    sport: selected_sport,
                    name: self.config.aux_remove_tag
                },
                on_response: function(response){
                    self.init_dashboard();
                },
    
                on_error: function(error){
                    self.login_error(error);
                    if(error.response['data']['error'] == 'error_remove_tag'){
                        alert(error.response['data']['description']);
                    }
                }});
                this.config.aux_remove_tag = null;
            },
    
            expanded_tags_list(sport){
                if (sport === undefined || sport == null || sport == 'none' || !(sport in this.preferences.tags_list)){
                    return this.preferences.tags_list['generic'];
                }
    
                return this.preferences.tags_list['generic'].concat(this.preferences.tags_list[sport]);
            },
        
            // for config panel
            expanded_config_tags_list(sport){
                if (sport === undefined || sport == null || sport == this.config.not_selected_sport){
                    return this.preferences.tags_list['generic'];
                }
    
                if(!(sport in this.preferences.tags_list)){
                    return [];
                }
    
                return this.preferences.tags_list[sport];
            },
    
            do_new_frame_tag(bvModalEvt){
                let self = this;
    
                let selected_sport;
                if(this.config.selected_sport != null && this.config.selected_sport != this.config.not_selected_sport){
                    selected_sport = this.config.selected_sport;
                }else{
                    selected_sport = null;
                }
    
                this.send_request({endpoint: Endpoints.PREFERENCES.TAGS.FRAME.ADD, method: 'POST', data: {
                    sport: selected_sport,
                    name: self.config.new_frame_tag
                },
                on_response: function(response){
                    self.init_dashboard();
                    self.config.new_frame_tag = null;
                },
    
                on_error: function(error){
                    self.login_error(error);
                    if(error.response['data']['error'] == 'error_add_frame_tag'){
                        alert(error.response['data']['description']);
                    }
                }});
            },
    
            prepare_remove_frame_tag(event, tag){
                event.preventDefault();
                event.stopPropagation();
    
                this.config.aux_remove_frame_tag = tag;
                this.$bvModal.show('remove-frame-tag');
    
            },
    
            do_remove_frame_tag(bvModalEvt){
                if(this.config.aux_remove_frame_tag == null)
                    return;
    
                let selected_sport;
                if(this.config.selected_sport != null && this.config.selected_sport != this.config.not_selected_sport){
                    selected_sport = this.config.selected_sport;
                }else{
                    selected_sport = null;
                }
    
                let self = this;
                this.send_request({endpoint: Endpoints.PREFERENCES.TAGS.FRAME.REMOVE, method: 'POST', data: {
                    sport: selected_sport,
                    name: self.config.aux_remove_frame_tag
                },
                on_response: function(response){
                    self.init_dashboard();
                },
    
                on_error: function(error){
                    self.login_error(error);
                    if(error.response['data']['error'] == 'error_remove_frame_tag'){
                        alert(error.response['data']['description']);
                    }
                }});
                this.config.aux_remove_frame_tag = null;
            },
    
            expanded_frame_tags_list(sport){
                if (sport === undefined || sport == null || sport == 'none' || !(sport in this.preferences.frame_tags_list)){
                    return this.preferences.frame_tags_list['generic'];
                }
    
                return this.preferences.frame_tags_list['generic'].concat(this.preferences.frame_tags_list[sport]);
            },
            
            // for config panel
            expanded_config_frame_tags_list(sport){
                if (sport === undefined || sport == null || sport == this.config.not_selected_sport){
                    return this.preferences.frame_tags_list['generic'];
                }
    
                if(!(sport in this.preferences.frame_tags_list)){
                    return [];
                }
    
                return this.preferences.frame_tags_list[sport];
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
                    self.login.message = ''; 
                    self.$cookie.set('token', response['data']['access_token']);
                    self.init_dashboard();
                },
    
                on_error: this.login_error
                });
            },
    
            /*
                FTP
            */
            do_ftp_credentials(){
                this.new_job.files_params.ftp.loading = true;
                let self = this;
                this.send_request({endpoint: Endpoints.JOBS.FTP.CREDENTIALS, method: 'GET',
                on_response: function(response){
                    self.new_job.files_params.ftp.host = response['data']['data']['credentials']['host'];
                    self.new_job.files_params.ftp.port = response['data']['data']['credentials']['port'];
                    self.new_job.files_params.ftp.token = response['data']['data']['credentials']['token'];
                    self.new_job.files_params.ftp.username = response['data']['data']['credentials']['username'];
                    self.new_job.files_params.ftp.password = response['data']['data']['credentials']['password'];
                    self.new_job.files_params.ftp.expiration = response['data']['data']['timeout'];
                },
    
                on_error: function(error){
                    self.login_error(error);
                    if(error.response['data']['error'] == 'error_job_ftp_config'){
                        self.new_job.message = error.response['description'];
                    }
                }});
            },
    
            do_start_ftp_upload(event, job){
                job.ftp_loading = true;
                let self = this;
                this.send_request({endpoint: Endpoints.JOBS.FTP.START, method: 'POST',
                data: {
                    job_id: job._id
                },
                on_response: function(response){
                    self.do_list_jobs();
                    job.ftp_loading = false;
                },
    
                on_error: function(error){
                    self.login_error(error);
                    if(error.response['data']['error'] == 'error_job_ftp_start'){
                        self.new_job.message = error.response['description'];
                    }
                }});
    
            },
    
            /*
                =============================
                JOBS
                =============================
            */
            /*
                CREATE JOB
            */
    
            do_new_job_clear(){
                this.new_job.name = '';
                this.new_job.comments = '';
                this.new_job.label_roi = true;
                this.new_job.camera = 'other';
                this.new_job.priority = 5;
                this.new_job.sport = null; //'none';
                this.new_job.tags = [];
                this.new_job.frame_tags = [];
                this.new_job.files_params = {
                    files: {
                        enable_autolabeling: true,
                        each_file_one_job: false,
                    },
                    video: {
                        enable_autolabeling: true,
                        start_time: new Date("1970-01-01T00:00:00Z"),
                        duration: null,
                        every: new Date("1970-01-01T00:00:01Z"),
                    },
                    zip: {
                        enable_autolabeling: true,
                        every: new Date("1970-01-01T00:00:01Z"),
                        each_file_one_job: false,
                    },
                    ftp: {
                        enable_autolabeling: true,
                        each_file_one_job: false,
                        loading: false,
                        username: null,
                        password: null,
                        token: null,
                        every: new Date("1970-01-01T00:00:01Z"),
                    },

                    corpus: {
                        glob_route: null,
                        each_file_one_job: false,
                        start_time: new Date("1970-01-01T00:00:00Z"),
                        duration: null,
                        every: new Date("1970-01-01T00:00:01Z"),
                    }
                };
                this.new_job.message = '';
                this.new_job.completed = false;

                this.new_job.order = 'ASCEND BY MOD. DATE';
                this.new_job.order_regex = null;
                this.new_job.order_show_details = false;
            },

            remove_job(event, job, remove_output){
                let self = this;
                if(!confirm("Remove " + job.name + " job?")){
                    return;
                }
                this.send_request({endpoint: Endpoints.JOBS.REMOVE, method: 'POST',
                data: {
                    job_id: job._id,
                    remove_output: remove_output
                },
                on_response: function(response){
                    self.do_list_jobs();
                    // refresh list
                    //self.$forceUpdate();

                },
    
                on_error: function(error){
                    self.login_error(error);
                }});
            },

            remove_entire_job(event, job, remove_output){
                let self = this;
                if(!confirm("Remove " + job.name + " job including his brothers?")){
                    return;
                }
                this.send_request({endpoint: Endpoints.JOBS.REMOVE_ENTIRE, method: 'POST',
                data: {
                    parent_id: job.variables.parent_id,
                    remove_output: remove_output
                },
                on_response: function(response){
                    self.do_list_jobs();
                    // refresh list
                    //self.$forceUpdate();

                },
    
                on_error: function(error){
                    self.login_error(error);
                }});
            },
    
            get_time_from_date(date){
                return (60 * 60 * date.getUTCHours()) + (60 * date.getUTCMinutes()) + date.getUTCSeconds();
            },
    
            get_file_params(){
                if(this.new_job.type_input == 'video'){
                    return {
                        enable_autolabeling: this.new_job.files_params.video.enable_autolabeling && this.has_autolabel_sport(this.new_job.sport),
                        each_file_one_job: this.new_job.files_params.each_file_one_job,
                        start_time: this.get_time_from_date(this.new_job.files_params.video.start_time),
                        duration: this.get_time_from_date(this.new_job.files_params.video.duration),
                        every: this.get_time_from_date(this.new_job.files_params.video.every)
                    };
                }
                else if(this.new_job.type_input == 'corpus'){
                   return {
                        enable_autolabeling: this.new_job.files_params.corpus.enable_autolabeling && this.has_autolabel_sport(this.new_job.sport),
                        each_file_one_job: this.new_job.files_params.each_file_one_job,
                        start_time: this.get_time_from_date(this.new_job.files_params.corpus.start_time),
                        duration: this.get_time_from_date(this.new_job.files_params.corpus.duration),
                        every: this.get_time_from_date(this.new_job.files_params.corpus.every),
                        glob_route: this.new_job.files_params.corpus.glob_route
                   };
                }
                else if(this.new_job.type_input == 'zip'){
                    return {
                        enable_autolabeling: this.new_job.files_params.zip.enable_autolabeling && this.has_autolabel_sport(this.new_job.sport),
                        each_file_one_job: this.new_job.files_params.zip.each_file_one_job,
                        every: this.get_time_from_date(this.new_job.files_params.zip.every)
                    }; 
    
                }else{
                    let aux = this.new_job.files_params[this.new_job.type_input];
                    if (this.new_job.files_params[this.new_job.type_input].every != undefined){
                        aux.every = this.get_time_from_date(this.new_job.files_params[this.new_job.type_input].every);
                    }
                    if('enable_autolabeling' in aux){
                        aux['enable_autolabeling'] = aux['enable_autolabeling'] && this.has_autolabel_sport(this.new_job.sport);
                    }
                    return aux;
                }
            },
    
            do_new_job_params(){
                let number_files = 1;
                if(Array.isArray(this.new_job.files)){
                    number_files = this.new_job.files.length;
                }
    
                return {
                    name: this.new_job.name,
                    comments: this.new_job.comments,
                    label_roi: this.new_job.label_roi,
                    camera: this.new_job.camera,
                    files_type: this.new_job.type_input,
                    files_params: JSON.stringify(this.get_file_params()),
                    sport: this.new_job.sport,
                    tags: JSON.stringify(this.new_job.tags),
                    frame_tags: JSON.stringify(this.new_job.frame_tags),
                    priority: this.new_job.priority,
                    pack_identifier: this.new_job.uuid,
                    number_files: number_files,
                    order: this.new_job.order,
                    order_regex: this.new_job.order_regex
                };
            },
    
            do_upload_files(files){
                let self = this;
                const r = new Resumable({
                  target: Endpoints.JOBS.CREATE,
                  query: self.do_new_job_params,
                  headers: { "Authorization": 'JWT ' + self.$cookie.get("token") },
                  testChunks: false
                  //simultaneousUploads: 10,
                  //chunkSize: 30 * 1024 * 1024, // 30mb 
                });
                if(!r.support) alert('Your browser does not support this feature'); //TODO: do better error handling
                r.on('fileSuccess', function(file){
                    //console.log('fileSuccess',file);
                });
                
                r.on('cancel', function(){
                    console.log('cancel');
                });
                
                r.on('fileAdded', function(file, event){
                    r.upload();
                });
    
                r.on('error', function(error){
                    error = JSON.parse(error);
                    if(error != undefined && error['error'] == "error_job_duplicated_name"){
                        self.new_job.message = error['description'];
                        return;
                    }
                });
    
                r.on('uploadStart', function(){
                    self.new_job.completed = false;
                    self.new_job.step = 'progress';
                });
    
                r.on('complete', function(){
                });
    
                r.on('progress', function(){
                   self.new_job.progress_bar = r.progress();
                   if(r.progress() == 1){
                        self.new_job.completed = true;
                        self.do_list_jobs(); 
                   }
                });
    
                if(!(Array.isArray(files))){
                    files =[files];
                }
    
                for(let i = 0; i < files.length; i++){
                    r.addFile(files[i]);
                }
                return r;
            },
    
            do_upload_nobrowser(){ // se suben ficheros que no estan en el navegador
                let params = this.do_new_job_params();
                const formData = new FormData();
                for(let k in params){
                  formData.append(k, params[k]);
                }
    
                this.new_job.files_params.ftp.loading = true;
                let self = this;
                this.send_request({endpoint: Endpoints.JOBS.CREATE, method: 'POST',
                data: formData,
                on_response: function(response){
                    self.new_job.step = 'progress';
                    self.new_job.progress_bar = 1;
                    self.new_job.completed = true;
                    self.do_list_jobs();
                },
    
                on_error: function(error){
                    self.login_error(error);
                }});
            },
    
            do_create_job(e){
                if(!(
                    (this.new_job.name != '' && this.new_job.name != null && this.new_job.name != undefined) &&
                    (this.new_job.sport != null && this.new_job.sport != undefined) //&& this.new_job.sport != 'none' && 
                    //(this.new_job.type_input != 'ftp' || this.new_job.files_params.ftp.username != null) &&
                    //(this.new_job.type_input == 'ftp' || this.new_job.files.length > 0)
                )){
                    // error
                    this.new_job.message = 'Fill all the necessary fields (Job name, files, sport).';
                    return;
                }  
                this.new_job.uuid = uuidv4();
                this.new_job.message = '';
                if(this.new_job.type_input == 'ftp' || this.new_job.type_input == 'corpus'){
                    this.do_upload_nobrowser(); // se suben ficheros que no estan en el navegador
                }else{
                    this.do_upload_files(this.new_job.files)
                }
            },
    
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
                if(this.list_jobs.selected_status != 'All'){
                    data_axios['data_uri'] = {'status': this.preferences.status_list.indexOf(this.list_jobs.selected_status)};
                }
                this.send_request(data_axios);
            },
    
            /*
                CHANGE JOB
            */
            do_change_visibility(job, value){
                let self = this;
                this.send_request({endpoint: Endpoints.JOBS.CHANGE_VISIBILITY, method: 'POST', data: {
                    job_id: job._id,
                    value: value
                },
                on_response: function(response){
                    job.visible = value;
                },
    
                on_error: function(error){
                    self.login_error(error);
                    if(error.response['data']['error'] == 'error_job_change_visibility'){
                        alert(error.response['data']['description']);
                    }
                }});
            },
    
            do_toggle_tag(event, job, tags_list, tag){
                let self = this;
                if(tags_list.includes(tag)){
                    tags_list.splice(tags_list.indexOf(tag), 1);
                }else{
                    tags_list.push(tag);
                }
    
                if(job != null){
                    this.send_request({endpoint: Endpoints.JOBS.CHANGE_TAGS, method: 'POST', data: {job_id: job._id, tags: tags_list}, on_response: function(){
                        job.tags = tags_list;
                    },
                    on_error: function(error){
                        self.login_error(error);
                        if(error.response['data']['error'] == 'error_job_change_tags'){
                            alert(error.response['data']['description']);
                        }
                    }});
                }
            },
    
            do_toggle_frame_tag(event, job, frame_tags_list, frame_tag){
                let self = this;
                if(frame_tags_list.includes(frame_tag)){
                    frame_tags_list.splice(frame_tags_list.indexOf(frame_tag), 1);
                }else{
                    frame_tags_list.push(frame_tag);
                }
    
                if(job != null){
                    this.send_request({endpoint: Endpoints.JOBS.FRAME.CHANGE_TAGS, method: 'POST', data: {job_id: job._id, frame_tags: frame_tags_list}, on_response: function(){
                        job.frame_tags = frame_tags_list;
                    },
                    on_error: function(error){
                        self.login_error(error);
                        if(error.response['data']['error'] == 'error_job_change_frame_tags'){
                            alert(error.response['data']['description']);
                        }
                    }});
                }
            },
    
            /*
                =============================
                USERS
                =============================
            */
            /*
                CREATE USER
            */
            do_create_user(){
                let self = this;
                this.send_request({endpoint: Endpoints.USERS.CREATE, method: 'POST', data: {
                    username: this.create_user.username,
                    password: this.create_user.password,
                    group: this.preferences.groups_list.indexOf(this.create_user.selected_group)
                },
                on_response: function(response){
                    self.create_user.step = 'message'; // Created
                    self.create_user.message = 'User successfully created.';
                    self.do_list_users();
                },
    
                on_error: function(error){
                    self.login_error(error);
                    if(error.response['data']['error'] == 'error_user_creation_duplicated' || error.response['data']['error'] == 'error_user_creation'){
                        self.create_user.step = 'message';
                        self.create_user.message = 'Duplicated user, create other';
                    }
                }
                });
            },
    
            /*
                LIST USERS
            */
            do_list_users(){
                let self = this;
                this.send_request({endpoint: Endpoints.USERS.LIST, method: 'GET', on_response: function(response){
                    self.list_users.users = response['data']['data'];
                },
                on_error: function(error){
                    self.login_error(error);
                    if(error.response['data']['error'] == 'error_user_list'){
                        alert(error.response['data']['description']);
                    }
    
                }});
            },
    
            /*
                CHANGE USERS
            */
            do_change_user_password(event, row, user_id){
                let self = this;
                this.send_request({endpoint: Endpoints.USERS.CHANGE_PASSWORD, method: 'POST', data: {
                    user_id: user_id,
                    password: this.change_user.password
                },
                on_response: function(response){
                    row.toggleDetails();
                },
    
                on_error: function(error){
                    self.login_error(error);
                    if(error.response['data']['error'] == 'error_user_change_password'){
                        alert(error.response['data']['description']);
                    }
    
                }});
            },

            toggle_user(event, user, enable){
                let self = this;
                let txt = (enable) ? 'Enable' : 'Disable'; 
                if(!confirm(txt + " " + user.username + " user?")){
                    return;
                }
                this.send_request({endpoint: Endpoints.USERS.TOGGLE, method: 'POST',
                data: {user_id: user._id, enable: enable},
                on_response: function(response){
                    self.do_list_users();
                    // refresh list
                    //self.$forceUpdate();

                },
    
                on_error: function(error){
                    self.login_error(error);
                }});
            },
    
            /*
                =============================
                METRICS
                =============================
            */
    
            do_get_metrics(){
                let self = this;
                this.send_request({endpoint: Endpoints.METRICS.GET, method: 'POST', 
                    data: {
                        job_id: self.metrics.job_id,
                        annotator_id: self.metrics.annotator_id,
                        group_by: self.metrics.group_by,
                    },
                    on_response: function(response){
                    self.metrics.list = response['data']['data'];
                },
                on_error: this.login_error});
            },
    
        },
    
        computed: {
            get_jobs_names(){
                let arr = [];
                for(let i = 0; i < this.list_jobs.jobs.length; i++){
                    arr.push(this.list_jobs.jobs[i].name);
                }
                return arr;
            },
    
            get_users_names(){
                let arr = [];
                for(let i = 0; i < this.list_users.users.length; i++){
                    arr.push(this.list_users.users[i].username);
                }
                return arr;
            },
    
            preferences_status_list_expanded(){
                let old_status = this.preferences.status_list.slice();
                old_status.splice(0, 0, 'All');
                return old_status;
            },
    
            preferences_expanded_sport_list(){
                return [this.config.not_selected_sport].concat(this.preferences.sports_list);
            }
            
        },
    
        mounted(){
            if(this.login.is_login){
                this.init_dashboard();
            }       
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

    textarea.comments{
        overflow: hidden; /*overflow is set to auto at max height using JS */
        font-family: sans-serif;
        outline: none;
        min-height: 100px;
        max-height: 314px;
        background-color: #fff;
    }
    :focus{
        outline: none !important;
    }
</style>