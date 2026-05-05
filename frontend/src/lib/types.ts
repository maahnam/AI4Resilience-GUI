export type MainWorkflow = 'training' | 'implementation' | 'comparison';
export type TrainingStep = 'dataset' | 'settings' | 'run';
export type ImplementationStep = 'dataset' | 'settings' | 'execute';
export type ComparisonStep = 'files' | 'compare';

export type ApiResponse<T = Record<string, never>> = T & {
	success: boolean;
	message?: string;
	error?: string;
};

export type DefaultConfig = {
	storage_cost: number;
	delay_penalty: number;
	undelivered_penalty: number;
	learning_rate: number;
	exploratory_rate: number;
	num_simulations: number;
	simulation_duration: number;
	impl_num_simulations: number;
	impl_duration: number;
};

export type DefaultFiles = {
	network: string;
	network_barge: string;
	network_train: string;
	network_truck: string;
	fixed_schedule: string;
	truck_schedule: string;
	demand: string;
	mode_costs: string;
	service_disruptions: string;
	demand_disruptions: string;
	q_table: string;
};

export type DefaultConfigPayload = ApiResponse<{
	config: DefaultConfig;
	default_files: DefaultFiles;
}>;

export type DatasetForm = {
	network: File | null;
	network_barge: File | null;
	network_train: File | null;
	network_truck: File | null;
	fixed_schedule: File | null;
	truck_schedule: File | null;
	demand: File | null;
	mode_costs: File | null;
	storage_cost: number;
	delay_penalty: number;
	undelivered_penalty: number;
	compute_kbest: boolean;
};

export type TrainingForm = {
	service_disruptions: File | null;
	demand_disruptions: File | null;
	last_q_table: File | null;
	last_total_cost: File | null;
	last_reward: File | null;
	learning_rate: number;
	exploratory_rate: number;
	num_simulations: number;
	simulation_duration: number;
	continue_training: boolean;
};

export type ImplementationForm = {
	service_disruptions: File | null;
	demand_disruptions: File | null;
	q_table: File | null;
	policy: 'gp' | 'aw' | 'ar';
	num_simulations: number;
	simulation_duration: number;
};

export type ComparisonForm = {
	file1: File | null;
	file2: File | null;
	label1: string;
	label2: string;
};

export type TrainingMetric = {
	Episode?: number;
	'Total Cost'?: number;
	'Total Reward'?: number;
	[key: string]: number | string | undefined;
};

export type SimulationMetric = {
	Episode?: number;
	'Total Cost'?: number;
	[key: string]: number | string | undefined;
};

export type TrainingProgress = {
	session_id: string;
	episode: number;
	total_episodes: number;
	data: TrainingMetric[];
};

export type SimulationProgress = {
	session_id: string;
	data: SimulationMetric[];
};

export type SeriesPoint = {
	label: string;
	value: number;
};
